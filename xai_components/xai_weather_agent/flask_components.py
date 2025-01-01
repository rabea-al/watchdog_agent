from xai_components.base import InArg, OutArg, InCompArg, Component, BaseComponent, xai_component, SubGraphExecutor, \
    dynalist
from flask import Flask, request, redirect, render_template, session, jsonify, stream_with_context, Response
from flask.views import View

import random
import string

FLASK_APP_KEY = 'flask_app'
FLASK_RES_KEY = 'flask_res'
FLASK_STREAMING_RES_KEY = 'flask_streaming_res'
FLASK_ROUTES_KEY = 'flask_routes'
FLASK_JOBS_KEY = 'flask_jobs'


def random_string(length):
    return ''.join(random.choice(string.ascii_letters) for _ in range(length))


class Route(View):
    def __init__(self, route, ctx):
        self.route = route
        self.ctx = ctx

    def dispatch_request(self, **kwargs):
        self.ctx[FLASK_RES_KEY] = ('', 204)
        self.route.parameters.value = kwargs
        SubGraphExecutor(self.route.body if hasattr(self.route, 'body') else self.route).do(self.ctx)
        response = self.ctx[FLASK_RES_KEY]
        return response


@xai_component
class FlaskCreateApp(Component):
    """Initializes a Flask application with optional configurations for static files and secret key.

    ##### inPorts:
    - name: The name of the Flask application.
    - public_path: The filesystem path to the folder containing static files. Default is 'public'.
    - static_url_path: The URL path at which the static files are accessible. Default is an empty string.
    - secret_key: A secret key used for session management and security. Default is 'opensesame'.
    """

    name: InCompArg[str]
    public_path: InArg[str]
    static_url_path: InArg[str]
    secret_key: InArg[str]

    def execute(self, ctx):
        ctx[FLASK_APP_KEY] = Flask(
            self.name.value,
            static_folder="public" if self.public_path.value is None else self.public_path.value,
            static_url_path="" if self.static_url_path.value is None else self.static_url_path.value
        )
        ctx[FLASK_APP_KEY].secret_key = "opensesame" if self.secret_key.value is None else self.secret_key.value

        for route in ctx.setdefault(FLASK_ROUTES_KEY, []):
            methods = [route.method] if hasattr(route, 'method') else route.methods.value
            endpoint_id = '%s_%s' % (route.route.value, "_".join(methods))
            ctx[FLASK_APP_KEY].add_url_rule(
                route.route.value,
                endpoint=endpoint_id,
                methods=methods,
                view_func=Route.as_view(route.route.value, route, ctx)
            )


@xai_component
class FlaskStartServer(Component):
    """ Starts the Flask Server

    """
    debug: InArg[bool]
    host: InArg[str]
    port: InArg[int]

    def execute(self, ctx):
        app = ctx[FLASK_APP_KEY]

        if 'flask_scheduler' in ctx:
            app.config.from_object(Config())

            scheduler = ctx['flask_scheduler']
            scheduler.init_app(app)
            scheduler.start()

        # Can't run debug mode from inside jupyter.
        app.run(
            debug=False if self.debug.value is None else self.debug.value,
            host="127.0.0.1" if self.host.value is None else self.host.value,
            port=8080 if self.port.value is None else self.port.value
        )

@xai_component
class FlaskInitScheduler(Component):
    """Initializes a scheduler for running background jobs in a Flask application.

    ##### Note:
    - This component must be executed before starting the server if background jobs are to be scheduled.
    """

    def execute(self, ctx):
        from flask_apscheduler import APScheduler

        scheduler = APScheduler()
        ctx['flask_scheduler'] = scheduler

        for task in ctx.setdefault(FLASK_JOBS_KEY, []):
            running_flag_key = 'flask_scheduler_' + task.job_id.value + '_running'
            @scheduler.task('interval', id=task.job_id.value, seconds=task.seconds.value,
                            misfire_grace_time=task.seconds.value)
            def job():
                app = ctx[FLASK_APP_KEY]
                if not ctx.setdefault(running_flag_key, False):
                    ctx[running_flag_key] = True

                    app.logger.info(f'Running interval job: {task.job_id.value}...')
                    try:
                        SubGraphExecutor(task).do(ctx)
                        app.logger.info(f'Interval job {task.job_id.value} done.')
                    except Exception as e:
                        app.logger.error(f'Interval job {task.job_id.value} failed with {e}.')
                    finally:
                        ctx[running_flag_key] = False
                else:
                    app.logger.info(f"Job {task.job_id.value} currently running.  Skipping execution.")


class Config:
    SCHEDULER_API_ENABLED = True


@xai_component(type='Start', color='red')
class FlaskCreateIntervalJob(Component):
    """Creates a scheduled interval job in a Flask application.

    ##### inPorts:
    - job_id: The identifier for the job.
    - seconds: The interval time in seconds between executions of the job.
    """
    job_id: InCompArg[str]
    seconds: InCompArg[int]

    def init(self, ctx):
        ctx.setdefault(FLASK_JOBS_KEY, []).append(self)


@xai_component
class FlaskInlineCreateIntervalJob(Component):
    """Creates a scheduled interval job in a Flask application.

    ##### inPorts:
    - job_id: The identifier for the job.
    - seconds: The interval time in seconds between executions of the job.

    ##### Branch:
    - body: The component to be executed when the job is triggered.
    """

    body: BaseComponent

    job_id: InCompArg[str]
    seconds: InCompArg[int]

    def execute(self, ctx):
        scheduler = ctx['flask_scheduler']

        try:
            scheduler.remove_job(self.job_id.value)
        except:
            pass

        running_flag_key = 'flask_scheduler_' + self.job_id.value + '_running'
        @scheduler.task('interval', id=self.job_id.value, seconds=self.seconds.value,
                        misfire_grace_time=self.seconds.value)
        def job():
            app = ctx[FLASK_APP_KEY]
            if not ctx.setdefault(running_flag_key, False):
                ctx[running_flag_key] = True

                app.logger.info(f'Running interval job: {self.job_id.value}...')
                try:
                    self.body.do(ctx)
                    app.logger.info(f'Interval job {self.job_id.value} done.')
                except Exception as e:
                    app.logger.error(f'Interval job {self.job_id.value} failed with {e}.')
                finally:
                    ctx[running_flag_key] = False
            else:
                app.logger.info(f"Job {self.job_id.value} currently running.  Skipping execution.")

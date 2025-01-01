from xai_components.base import InArg, OutArg, InCompArg, Component, BaseComponent, xai_component, dynalist
import sqlite3


@xai_component
class SqliteOpenDB(Component):
    """Opens a connection to the SQLite database.

    This component opens a connection to a specified SQLite database file and prepares the database for executing queries.

    ##### inPorts:
    - file_name: Name of the SQLite database file to connect to.

    ##### outPorts:
    -  A callable function that returns the database connection.
    """
    file_name: InCompArg[str]

    def execute(self, ctx):
        def get_db():
            db = sqlite3.connect(self.file_name.value)
            db.row_factory = sqlite3.Row
            return db

        ctx['sqlite_get_db'] = get_db


@xai_component
class SqliteWithTransaction(Component):
    """Executes multiple SQLite operations in a transaction.

    This component ensures that all SQLite operations inside the transaction are either fully completed or rolled back in case of an error.

    ##### inPorts:
    - A function to retrieve the SQLite database connection.

    ##### outPorts:
    - in_transaction: The component or series of operations to be executed within the transaction.
    - The SQLite database connection used in the transaction.
    """
    in_transaction: BaseComponent

    def execute(self, ctx):
        db = ctx['sqlite_get_db']()
        with db:
            ctx['sqlite_db'] = db
            next = self.in_transaction
            while next:
                next = next.do(ctx)
        db.close()
        ctx['sqlite_db'] = None


@xai_component
class SqliteExecute(Component):
    """Executes an SQL query on the SQLite database.

    This component executes a specified SQL query, with or without parameters, on the currently open SQLite database.

    ##### inPorts:
    - query: The SQL query to execute.
    - args: A list of arguments to pass into the SQL query (optional).

    ##### outPorts:
    - result: A message indicating the success or failure of the query execution.
    """
    query: InCompArg[str]
    args: InArg[dynalist]
    result: OutArg[str]

    def execute(self, ctx):
        db = ctx['sqlite_db']
        try:
            if self.args.value is None:
                db.execute(self.query.value)
            else:
                db.execute(self.query.value, tuple(self.args.value))
            self.result.value = "Query executed successfully."
        except Exception as e:
            self.result.value = f"Error: {str(e)}"



@xai_component
class SqliteExecuteScript(Component):
    """Executes a SQL script from a file on the SQLite database.

    This component reads an SQL script from a file and executes it on the currently open SQLite database.

    ##### inPorts:
    - file_path: Path to the SQL script file.


    """
    file_path: InCompArg[str]

    def execute(self, ctx):
        db = ctx['sqlite_db']

        with open(self.file_path.value, 'r') as f:
            db.cursor().executescript(f.read())


@xai_component
class SqliteFetchOne(Component):
    """Fetches a single row from the SQLite database.

    This component executes a query and fetches one row from the database result set.

    ##### inPorts:
    - query: The SQL query to execute.
    - args: A list of arguments to pass into the query (optional).

    ##### outPorts:
    - result: The fetched row, returned as a dictionary.
    """
    query: InCompArg[str]
    args: InArg[dynalist]
    result: OutArg[dict]

    def execute(self, ctx):
        db = ctx['sqlite_db']

        if self.args.value is None:
            value = db.execute(self.query.value).fetchone()
            self.result.value = {k: value[k] for k in value.keys()}
        else:
            value = db.execute(self.query.value, tuple(self.args.value)).fetchone()
            self.result.value = {k: value[k] for k in value.keys()}

@xai_component
class SqliteFetchAll(Component):
    """Fetches all rows from the SQLite database.

    This component executes a query and fetches all rows from the database result set.

    ##### inPorts:
    - query: The SQL query to execute.
    - args: A list of arguments to pass into the query (optional).

    ##### outPorts:
    - result: A list of rows, each returned as a dictionary.
    """
    query: InCompArg[str]
    args: InArg[dynalist]
    result: OutArg[list]

    def execute(self, ctx):
        db = ctx['sqlite_db']

        if self.args.value is None:
            values = db.execute(self.query.value).fetchall()
        else:
            values = db.execute(self.query.value, tuple(self.args.value)).fetchall()

        ret = []
        for item in values:
            ret.append({k: item[k] for k in item.keys()})

        formatted_result = "\n".join(
            [", ".join(f"{key}: {value}" for key, value in row.items()) for row in ret]
        )

        self.result.value = formatted_result
        print(f"Formatted Result: {formatted_result}")


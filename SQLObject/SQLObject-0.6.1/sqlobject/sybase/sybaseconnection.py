from sqlobject.dbconnection import DBAPI
Sybase = None

class SybaseConnection(DBAPI):

    supportTransactions = False
    dbName = 'sybase'
    schemes = [dbName]

    def __init__(self, db, user, passwd='', host='localhost',
                 locking=1, **kw):
        db = db.strip('/')
        global Sybase
        if Sybase is None:
            import Sybase
            Sybase._ctx.debug = 0
            from Sybase import NumericType
            from sqlobject.converters import registerConverter, IntConverter
            registerConverter(NumericType, IntConverter)
        self.module = Sybase
        self.locking = int(locking)
        self.host = host
        self.db = db
        self.user = user
        self.passwd = passwd
        autoCommit = kw.get('autoCommit')
        if autoCommit:
           autoCommmit = int(autoCommit)
        else:
            autoCommit = None
        kw['autoCommit'] = autoCommit
        DBAPI.__init__(self, **kw)

    def connectionFromURI(cls, uri):
        user, password, host, path, args = cls._parseURI(uri)
        return cls(user=user, passwd=password, host=host or 'localhost',
                   db=path, **args)
    connectionFromURI = classmethod(connectionFromURI)

    def insert_id(self, conn):
        """
        Sybase adapter/cursor does not support the
        insert_id method.
        """
        c = conn.cursor()
        c.execute('SELECT @@IDENTITY')
        return c.fetchone()[0]

    def makeConnection(self):
        return Sybase.connect(self.host, self.user, self.passwd,
                              database=self.db, auto_commit=self.autoCommit,
                              locking=self.locking)

        
    HAS_IDENTITY = """
       SELECT col.name, col.status, obj.name
       FROM syscolumns col
       JOIN sysobjects obj
       ON obj.id = col.id
       WHERE obj.name = '%s'
             AND (col.status & 0x80) = 0x80
             
    """
    def _hasIdentity(self, conn, table):
        query = self.HAS_IDENTITY % table
        c = conn.cursor()
        c.execute(query)
        r = c.fetchone()
        return r is not None
        
    def _queryInsertID(self, conn, soInstance, id, names, values):
        table = soInstance._table
        idName = soInstance._idName
        c = conn.cursor()
        if id is not None:
            names = [idName] + names
            values = [id] + values

        has_identity = self._hasIdentity(conn, table)
        if has_identity:
            if id is not None:
                c.execute('SET IDENTITY_INSERT %s ON' % table)
            else:
                c.execute('SET IDENTITY_INSERT %s OFF' % table)

        q = self._insertSQL(table, names, values)
        if self.debug:
            print 'QueryIns: %s' % q
        c.execute(q)
        if has_identity:
            c.execute('SET IDENTITY_INSERT %s OFF' % table)
        if id is None:
            id = self.insert_id(conn)
        if self.debugOutput:
            self.printDebug(conn, id, 'QueryIns', 'result')
        return id

    def _queryAddLimitOffset(self, query, start, end):
        # XXX Sybase doesn't support LIMIT
        return query

    def createColumn(self, soClass, col):
        return col.sybaseCreateSQL()

    def createIDColumn(self, soClass):
        return '%s NUMERIC(18,0) IDENTITY UNIQUE' % soClass._idName

    def createIndexSQL(self, soClass, index):
        return index.sybaseCreateIndexSQL(soClass)

    def joinSQLType(self, join):
        return 'NUMERIC(18,0) NOT NULL'

    SHOW_TABLES="SELECT name FROM sysobjects WHERE type='U'"
    def tableExists(self, tableName):
        for (table,) in self.queryAll(self.SHOW_TABLES):
            if table.lower() == tableName.lower():
                return True
        return False

    def addColumn(self, tableName, column):
        self.query('ALTER TABLE %s ADD COLUMN %s' %
                   (tableName,
                    column.sybaseCreateSQL()))

    def delColumn(self, tableName, column):
        self.query('ALTER TABLE %s DROP COLUMN %s' %
                   (tableName,
                    column.dbName))

    SHOW_COLUMNS=("select 'column' = COL_NAME(id, colid) "
                  "from syscolumns where id = OBJECT_ID(%s)")
    def columnsFromSchema(self, tableName, soClass):
        colData = self.queryAll(self.SHOW_COLUMNS
                                % tableName)
        results = []
        for field, t, nullAllowed, key, default, extra in colData:
            if field == 'id':
                continue
            colClass, kw = self.guessClass(t)
            kw['name'] = soClass._style.dbColumnToPythonAttr(field)
            kw['notNone'] = not nullAllowed
            kw['default'] = default
            # @@ skip key...
            # @@ skip extra...
            results.append(colClass(**kw))
        return results

    def _setAutoCommit(self, conn, auto):
        conn.auto_commit = auto

    def guessClass(self, t):
        if t.startswith('int'):
            return col.IntCol, {}
        elif t.startswith('varchar'):
            return col.StringCol, {'length': int(t[8:-1])}
        elif t.startswith('char'):
            return col.StringCol, {'length': int(t[5:-1]),
                                   'varchar': False}
        elif t.startswith('datetime'):
            return col.DateTimeCol, {}
        else:
            return col.Col, {}

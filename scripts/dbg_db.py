import importlib.util
import tempfile, os

# Load database.db_manager by file path to avoid package import issues
db_path_file = os.path.join(os.path.dirname(__file__), '..', 'database', 'db_manager.py')
db_path_file = os.path.abspath(db_path_file)
spec = importlib.util.spec_from_file_location('database.db_manager', db_path_file)
db_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(db_module)
DatabaseManager = db_module.DatabaseManager

tmpdir = tempfile.mkdtemp()
path = os.path.join(tmpdir, 'test.db')
print('db path:', path)
try:
    db = DatabaseManager(db_path=path)
    conn = db.get_connection()
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table'")
    print('tables:', c.fetchall())
    conn.close()
except Exception as e:
    print('error:', e)

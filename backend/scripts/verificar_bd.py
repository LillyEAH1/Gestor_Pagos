import psycopg, os
url = os.environ["DATABASE_URL"]
with psycopg.connect(url) as conn:
    total = conn.execute("SELECT COUNT(*) FROM proveedores").fetchone()[0]
    sin_clabe = conn.execute("SELECT COUNT(*) FROM proveedores WHERE clabe='' OR clabe IS NULL").fetchone()[0]
    con_clabe = conn.execute("SELECT COUNT(*) FROM proveedores WHERE clabe!='' AND clabe IS NOT NULL").fetchone()[0]
    print(f"Total proveedores en BD: {total}")
    print(f"Con CLABE: {con_clabe}")
    print(f"Sin CLABE (contado/efectivo/etc): {sin_clabe}")

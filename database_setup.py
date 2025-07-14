import pyodbc

CONEXION_STRING_SETUP = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=PC-MIMI\\SQLEXPRESS;"  
    "DATABASE=parqueo_db;"        
    "Trusted_Connection=yes;"
)

def inicializar_db():
    """
    Inicializa la base de datos SQL Server y crea las tablas necesarias.
    """
    conn = None
    try:
        conn = pyodbc.connect(CONEXION_STRING_SETUP)
        cursor = conn.cursor()

        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='propietarios' and xtype='U')
            CREATE TABLE propietarios (
                cedula NVARCHAR(255) PRIMARY KEY,
                nombre NVARCHAR(255) NOT NULL,
                telefono NVARCHAR(255) NOT NULL,
                direccion NVARCHAR(255) NOT NULL
            )
        """)

        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='vehiculos' and xtype='U')
            CREATE TABLE vehiculos (
                placa NVARCHAR(255) PRIMARY KEY,
                marca NVARCHAR(255) NOT NULL,
                modelo NVARCHAR(255) NOT NULL,
                propietario_cedula NVARCHAR(255) NOT NULL,
                FOREIGN KEY (propietario_cedula) REFERENCES propietarios(cedula) ON DELETE CASCADE
            )
        """)

        
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='registros' and xtype='U')
            CREATE TABLE registros (
                id INT IDENTITY(1,1) PRIMARY KEY, -- Sintaxis SQL Server para auto-incremento
                placa_vehiculo NVARCHAR(255) NOT NULL,
                hora_entrada DATETIME NOT NULL,
                hora_salida DATETIME,
                espacio_asignado NVARCHAR(255),
                FOREIGN KEY (placa_vehiculo) REFERENCES vehiculos(placa) ON DELETE CASCADE
            )
        """)

        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='facturas' and xtype='U')
            CREATE TABLE facturas (
                id INT IDENTITY(1,1) PRIMARY KEY, -- Sintaxis SQL Server para auto-incremento
                registro_id INT NOT NULL,
                placa NVARCHAR(255) NOT NULL,
                tiempo_total_minutos REAL NOT NULL,
                monto_cobrado REAL NOT NULL,
                fecha_emision DATETIME NOT NULL,
                FOREIGN KEY (registro_id) REFERENCES registros(id)
            )
        """)

        conn.commit()
        print(f"Tablas de la base de datos SQL Server 'parqueo_db' creadas/actualizadas exitosamente.")

    except pyodbc.Error as ex:
        print(f"Error de base de datos durante la inicialización: {ex}")
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    inicializar_db()
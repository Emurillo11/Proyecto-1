import pyodbc
from collections import deque
from datetime import datetime

CONEXION_STRING = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=PC-MIMI\\SQLEXPRESS;"  
    "DATABASE=parqueo_db;"       
    "Trusted_Connection=yes;"     
)

TARIFA_POR_MINUTO = 15 

class DatabaseManager:
    """
    Clase para manejar las operaciones con la base de datos SQL Server.
    """
    def ejecutar_query(self, query, params=(), fetchone=False, fetchall=False):
        conn = None
        try:
            conn = pyodbc.connect(CONEXION_STRING)
            cursor = conn.cursor()
            
            cursor.execute(query, params)

            
            result_data = None
            if fetchone:
                row = cursor.fetchone()
                if row:
                    columns = [column[0] for column in cursor.description]
                    result_data = dict(zip(columns, row))
            elif fetchall:
                columns = [column[0] for column in cursor.description]
                result_data = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            
            conn.commit()

            if fetchone or fetchall:
                return result_data
            
            return True

        except pyodbc.Error as ex:
            print(f"Error de base de datos en ejecutar_query: {ex}")
           
            if conn:
                conn.rollback()
            return False 
        finally:
            if conn:
                conn.close()


class Propietario:
    db = DatabaseManager() 

    @classmethod
    def agregar(cls, cedula, nombre, telefono, direccion):
        query = "INSERT INTO propietarios (cedula, nombre, telefono, direccion) VALUES (?, ?, ?, ?)"
        
        return cls.db.ejecutar_query(query, (cedula, nombre, telefono, direccion))

    @classmethod
    def todos(cls):
        
        return cls.db.ejecutar_query("SELECT * FROM propietarios ORDER BY nombre ASC", fetchall=True)

class Vehiculo:
    db = DatabaseManager() 

    @classmethod
    def agregar(cls, placa, marca, modelo, propietario_cedula):
        query = "INSERT INTO vehiculos (placa, marca, modelo, propietario_cedula) VALUES (?, ?, ?, ?)"
        
        return cls.db.ejecutar_query(query, (placa, marca, modelo, propietario_cedula))

    @classmethod
    def buscar(cls, placa):
       
        return cls.db.ejecutar_query("SELECT * FROM vehiculos WHERE placa = ?", (placa,), fetchone=True)

    @classmethod
    def esta_estacionado(cls, placa):
        
        query = "SELECT id FROM registros WHERE placa_vehiculo = ? AND hora_salida IS NULL"
        return cls.db.ejecutar_query(query, (placa,), fetchone=True) is not None

class Facturacion:
    db = DatabaseManager() 

    def generar_factura(self, placa):
        
        query_registro = """
            SELECT TOP 1 id, hora_entrada, hora_salida FROM registros
            WHERE placa_vehiculo = ? AND hora_salida IS NOT NULL
            ORDER BY hora_salida DESC
        """
        registro = self.db.ejecutar_query(query_registro, (placa,), fetchone=True)
        
        if not registro:
            
            raise Exception("No se encontró un registro de salida válido para facturar para la placa: " + placa)

        formato_fecha = "%Y-%m-%d %H:%M:%S"
        
        
        hora_entrada_str = str(registro['hora_entrada']).split('.')[0]
        hora_salida_str = str(registro['hora_salida']).split('.')[0]
        
        hora_entrada = datetime.strptime(hora_entrada_str, formato_fecha)
        hora_salida = datetime.strptime(hora_salida_str, formato_fecha)
        
        
        duracion = hora_salida - hora_entrada
        total_minutos = round(duracion.total_seconds() / 60, 2)
        monto_total = total_minutos * TARIFA_POR_MINUTO
        
        
        query_factura = """
            INSERT INTO facturas (registro_id, placa, tiempo_total_minutos, monto_cobrado, fecha_emision)
            OUTPUT INSERTED.id -- Esta cláusula devuelve el ID de la fila recién insertada
            VALUES (?, ?, ?, ?, ?)
        """
        fecha_emision = datetime.now().strftime(formato_fecha)
        
        resultado = self.db.ejecutar_query(
            query_factura,
            (registro['id'], placa, total_minutos, monto_total, fecha_emision),
            fetchone=True 
        )
        
        
        if resultado is not None and isinstance(resultado, dict) and 'id' in resultado:
            factura_id = resultado['id']
            return factura_id
        else:
            raise Exception("No se pudo obtener el ID de la factura generada. Posible fallo en la inserción o en la consulta OUTPUT.")

    @classmethod
    def obtener_factura(cls, factura_id):
        
        query = """
            SELECT f.id, f.placa, f.tiempo_total_minutos, f.monto_cobrado, f.fecha_emision,
                   r.hora_entrada, r.hora_salida, r.espacio_asignado,
                   p.nombre as propietario_nombre, p.cedula
            FROM facturas f
            JOIN registros r ON f.registro_id = r.id
            JOIN vehiculos v ON f.placa = v.placa
            JOIN propietarios p ON v.propietario_cedula = p.cedula
            WHERE f.id = ?
        """
        return cls.db.ejecutar_query(query, (factura_id,), fetchone=True)

class Parqueo:
    db = DatabaseManager() 

    def __init__(self, filas, columnas):
        self.filas = filas
        self.columnas = columnas
        self.mapa = [] 
        self.lista_espera = deque() 
        self.actualizar_estado_desde_db() 

    def actualizar_estado_desde_db(self):
        
        self.mapa = [[None for _ in range(self.columnas)] for _ in range(self.filas)]
        query = "SELECT placa_vehiculo, espacio_asignado FROM registros WHERE hora_salida IS NULL"
        vehiculos_activos = self.db.ejecutar_query(query, fetchall=True)
        
        
        if not vehiculos_activos or vehiculos_activos is False: return

        for vehiculo in vehiculos_activos:
            espacio = vehiculo['espacio_asignado']
            try:
                
                fila = int(espacio.split(',')[0].replace('F', '')) - 1
                col = int(espacio.split(',')[1].replace('C', '')) - 1
                if 0 <= fila < self.filas and 0 <= col < self.columnas:
                    self.mapa[fila][col] = vehiculo['placa_vehiculo']
            except (ValueError, IndexError, AttributeError):
                    print(f"Advertencia: Espacio asignado '{espacio}' tiene un formato incorrecto o faltan claves.")

    def encontrar_espacio_libre(self):
        self.actualizar_estado_desde_db() 
        for i in range(self.filas):
            for j in range(self.columnas):
                if self.mapa[i][j] is None:
                    return (i, j) 
        return None 

    def registrar_entrada(self, placa):
        if not Vehiculo.buscar(placa):
            return "Error: Vehículo no registrado en el sistema."
        if Vehiculo.esta_estacionado(placa):
            return f"Error: El vehículo {placa} ya se encuentra dentro del parqueo."

        espacio = self.encontrar_espacio_libre()
        if espacio:
            fila, col = espacio
            query = "INSERT INTO registros (placa_vehiculo, hora_entrada, espacio_asignado) VALUES (?, ?, ?)"
            hora_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            espacio_str = f"F{fila+1},C{col+1}"
            
            
            if self.db.ejecutar_query(query, (placa, hora_actual, espacio_str)):
                self.mapa[fila][col] = placa 
                return f"Vehículo {placa} ingresó al espacio {espacio_str}."
            else:
                return "Error: Fallo al registrar la entrada del vehículo en la base de datos."
        else:
            
            if placa not in self.lista_espera:
                self.lista_espera.append(placa)
            return f"Parqueo lleno. Vehículo {placa} agregado a la lista de espera."

    def registrar_salida(self, placa):
        hora_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        query = "UPDATE registros SET hora_salida = ? WHERE placa_vehiculo = ? AND hora_salida IS NULL"
        
        
        if self.db.ejecutar_query(query, (hora_actual, placa)):
            mensaje_salida = f"Vehículo {placa} ha salido. Generando factura..."
            
            if self.lista_espera:
                placa_en_espera = self.lista_espera.popleft()
                mensaje_entrada = self.registrar_entrada(placa_en_espera)
                return f"{mensaje_salida} {mensaje_entrada}"
            return mensaje_salida
        else:
            return "Error: Fallo al registrar la salida del vehículo en la base de datos."
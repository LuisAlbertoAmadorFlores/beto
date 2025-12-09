import mysql.connector
from mysql.connector import Error
 
def crear_conexion():
 
    conexion = None
    
    try:
        conexion = mysql.connector.connect(
            host="26.165.234.2",  # O la IP de tu servidor
            user="amador",  # Por ejemplo, 'root'
            password="Amador09_",  # Tu contraseña de MySQL
            database="nxgcommx_intranet_cya",  # La base de datos a usar
        ) 
    
        if conexion.is_connected():
            print("Conexion Existosa")
            return conexion
    except Error as e:
        print("Error al conectar a MySQL!")
        return conexion

def cerrar_conexion(conexion):
    if conexion and conexion.is_connected():
        conexion.close()
        print("conexion cerrada")
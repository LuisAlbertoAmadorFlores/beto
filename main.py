from fastapi import FastAPI
from conexion import crear_conexion, cerrar_conexion


app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/check/document/{idColaborador}")
async def read_Data(idColaborador):

    data = await getData(idColaborador)
    return {"data": data}


async def getData(idColaborador):
    try:
        connect= crear_conexion()
        if connect.is_connected():
            # print("!Conexion Exitosa¡")
            cursor = connect.cursor()
            sql = "SELECT * FROM colaborador WHERE idColaborador =%s"
            cursor.execute(sql, (idColaborador,))
            
            resultado = cursor.fetchall()

            return resultado

    except Exception as e:
        print(f"Error:{e}")
        return []
    finally:
        if "conexion" in locals() and connect.is_connected():
            cursor.close()
            cerrar_conexion(connect)
            print("Conexion cerrada.")

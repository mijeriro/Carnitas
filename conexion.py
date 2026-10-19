import json
import os
from dotenv import load_dotenv
import psycopg2
import mssql_python
class Conexion_sqlserver:
    def __init__(self):
        load_dotenv()
        self.__SERVER = os.environ.get("SERVER_NAME")
        self.__DATABASE = os.environ.get("DATABASE_NAME")
        self.__USER = os.environ.get("USER")
        self.__PASSWORD = os.environ.get("PASSWORD")
        self.__CNX = None #Gestionar la conexion
        self.__CURSOR = None #Gestionar las consultas

    def crear_conexion(self):
        try:
            SQL_CONNECTION_STRING= (
                f"Server={self.__SERVER};"
                f"Database={self.__DATABASE};"
                f"UID={self.__USER};"
                f"PWD={self.__PASSWORD};"
                "Encrypt=YES;"
                "TrustServerCertificate=YES;"
            )
            self.__CNX = mssql_python.connect(SQL_CONNECTION_STRING)
            self.__CURSOR = self.__CNX.cursor()
            print(f"Conectado al servidor {self.__SERVER}")
            return self.__CNX
        except mssql_python.Error as e:
            print(f"Error al conectarse servidor {self.__SERVER} de Base de Datos")
            print(e)
            self.__CNX = None
            self.__CURSOR = None
            return None

    def ejecutar(self, sql, parametros=None):
        try:
            # Verificar conexión
            if self.__CNX is None:
                # Intento conectarme
                if self.crear_conexion() is None:
                    return json.dumps(
                        {
                            "estado": False,
                            "mensaje": "No fue posible establecer la conexión"
                        },
                        ensure_ascii=False
                    )

            # Ejecutar consulta
            if parametros:
                self.__CURSOR.execute(
                    sql,
                    parametros
                )
            else:
                self.__CURSOR.execute(sql)

            # Identificar operación
            tipo = sql.strip().split()[0].upper()
            # SELECT
            if tipo == "SELECT":
                columnas = []
                for columna in self.__CURSOR.description:
                    columnas.append(columna[0])

                # Obtener registros
                registros = self.__CURSOR.fetchall()

                resultado = []
                for registro in registros:
                    fila = {}
                    for i, valor in enumerate(registro):
                        fila[columnas[i]] = valor
                    resultado.append(fila)

                return json.dumps(
                    {
                        "estado": True,
                        "tipo": "SELECT",
                        "registros": resultado
                    },
                    default=str,  # Si no sabe como convertir, aplicale la funcion str()
                    ensure_ascii=False  # Para caracteres latinoamericanos
                )
            # INSERT
            elif tipo == "INSERT":
                filas = self.__CURSOR.rowcount  # Obtine el numero de rgistros afectados
                self.__CNX.commit()  # Comete la transacción
                return json.dumps(
                    {
                        "estado": True,
                        "tipo": "INSERT",
                        "mensaje": "Registro insertado correctamente",
                        "filas_afectadas": filas
                    },
                    ensure_ascii=False
                )
            # UPDATE
            elif tipo == "UPDATE":
                filas = self.__CURSOR.rowcount
                self.__CNX.commit()
                return json.dumps(
                    {
                        "estado": True,
                        "tipo": "UPDATE",
                        "mensaje": "Registro actualizado correctamente",
                        "filas_afectadas": filas
                    },
                    ensure_ascii=False
                )
            # DELETE
            elif tipo == "DELETE":
                filas = self.__CURSOR.rowcount
                self.__CNX.commit()
                return json.dumps(
                    {
                        "estado": True,
                        "tipo": "DELETE",
                        "mensaje": "Registro eliminado correctamente",
                        "filas_afectadas": filas
                    },
                    ensure_ascii=False
                )
            # OTRAS OPERACIONES
            else:
                filas = self.__CURSOR.rowcount
                self.__CNX.commit()
                return json.dumps(
                    {
                        "estado": True,
                        "tipo": tipo,
                        "mensaje": "Consulta ejecutada correctamente",
                        "filas_afectadas": filas
                    },
                    ensure_ascii=False
                )
        # ERROR DE INTEGRIDAD
        except mssql_python.IntegrityError as e:
            if self.__CNX:
                self.__CNX.rollback()
            return json.dumps(
                {
                    "estado": False,
                    "tipo": "IntegrityError",
                    "mensaje": "Violación de integridad en la base de datos",
                    "error": str(e)
                },
                ensure_ascii=False
            )
        # ERROR DE PROGRAMACIÓN SQL
        except mssql_python.ProgrammingError as e:
            if self.__CNX:
                self.__CNX.rollback()
            return json.dumps(
                {
                    "estado": False,
                    "tipo": "ProgrammingError",
                    "mensaje": "Error en la consulta SQL",
                    "error": str(e)
                },
                ensure_ascii=False
            )
        # ERROR GENERAL
        except mssql_python.Error as e:
            if self.__CNX:
                self.__CNX.rollback()
            return json.dumps(
                {
                    "estado": False,
                    "tipo": "DatabaseError",
                    "mensaje": "Error en la base de datos",
                    "error": str(e)
                },
                ensure_ascii=False
            )
        # ERROR DE PYTHON
        except Exception as e:
            if self.__CNX:
                self.__CNX.rollback()
            return json.dumps(
                {
                    "estado": False,
                    "tipo": "Error",
                    "mensaje": "Error inesperado",
                    "error": str(e)
                },
                ensure_ascii=False
            )

    def cerrar_conexion(self):
        try:
            if self.__CURSOR:
                self.__CURSOR.close()
                self.__CURSOR = None
            if self.__CNX:
                self.__CNX.close()
                self.__CNX = None
            print(f"Se a cerrado la conexion al seridor {self.__SERVER}")
            return True
        except mssql_python.Error as e:
            print("Error al desconectarse del servidro de base de datos")
            print(e)
            return False



class Conexion_psql:
    def __init__(self):
        load_dotenv()
        self.__SERVER = os.environ.get("DB_HOST", "localhost")
        self.__PORT = os.environ.get("DB_PORT", "5432")
        self.__DATABASE = os.environ.get("DB_NAME")
        self.__USER = os.environ.get("DB_USER")
        self.__PASSWORD = os.environ.get("DB_PASSWORD")
        self.__CNX = None
        self.__CURSOR = None

    def crear_conexion(self):
        try:
            self.__CNX = psycopg2.connect(
                host=self.__SERVER,
                port=self.__PORT,
                dbname=self.__DATABASE,
                user=self.__USER,
                password=self.__PASSWORD,
            )
            self.__CURSOR = self.__CNX.cursor()
            print(f"Conectado al servidor {self.__SERVER}")
            return self.__CNX
        except psycopg2.Error as e:
            print(f"Error al conectarse servidor {self.__SERVER} de Base de Datos")
            print(e)
            self.__CNX = None
            self.__CURSOR = None
            return None

    def consulta(self, sql, parametros=None):
        try:
            # Verificar conexión
            if self.__CNX is None:
                if self.crear_conexion() is None:
                    return json.dumps(
                        {
                            "estado": False,
                            "mensaje": "No fue posible establecer la conexión",
                        },
                        ensure_ascii=False,
                    )

            if parametros:
                self.__CURSOR.execute(sql, parametros)
            else:
                self.__CURSOR.execute(sql)

            tipo = sql.strip().split()[0].upper()

            if tipo == "SELECT":
                columnas = [columna[0] for columna in self.__CURSOR.description]
                registros = self.__CURSOR.fetchall()
                resultado = []
                for registro in registros:
                    fila = {}
                    for i, valor in enumerate(registro):
                        fila[columnas[i]] = valor
                    resultado.append(fila)
                return json.dumps(
                    {"estado": True, "tipo": "SELECT", "registros": resultado},
                    default=str,  # Decimal, datetime, etc. se convierten con str()
                    ensure_ascii=False,
                )

            # INSERT, UPDATE, DELETE
            mensajes = {
                "INSERT": "Registro insertado correctamente",
                "UPDATE": "Registro actualizado correctamente",
                "DELETE": "Registro eliminado correctamente",
            }
            filas = self.__CURSOR.rowcount  # Registros afectados
            self.__CNX.commit()
            return json.dumps(
                {
                    "estado": True,
                    "tipo": tipo,
                    "mensaje": mensajes.get(tipo, "Consulta ejecutada correctamente"),
                    "filas_afectadas": filas,
                },
                ensure_ascii=False,
            )

        except psycopg2.IntegrityError as e:
            return self.__error("IntegrityError", "Violación de integridad en la base de datos", e)

        except psycopg2.ProgrammingError as e:
            return self.__error("ProgrammingError", "Error en la consulta SQL", e)

        except psycopg2.Error as e:
            return self.__error("DatabaseError", "Error en la base de datos", e)

        except Exception as e:
            return self.__error("Error", "Error inesperado", e)

    def __error(self, tipo, mensaje, e):
        if self.__CNX:
            self.__CNX.rollback()
        return json.dumps(
            {"estado": False, "tipo": tipo, "mensaje": mensaje, "error": str(e)},
            ensure_ascii=False,
        )

    def cerrar_conexion(self):
        try:
            if self.__CURSOR:
                self.__CURSOR.close()
                self.__CURSOR = None
            if self.__CNX:
                self.__CNX.close()
                self.__CNX = None
            print(f"Se ha cerrado la conexion al servidor {self.__SERVER}")
            return True
        except psycopg2.Error as e:
            print("Error al desconectarse del servidor de base de datos")
            print(e)
            return False



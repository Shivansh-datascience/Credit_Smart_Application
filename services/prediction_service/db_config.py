from pymysql.connections import CLIENT
import pymysql
from sqlalchemy.engine import create_engine , create_pool_from_url
from pymysql.cursors import Cursor
from pymysql.err import MySQLError , InternalError
import os
from dotenv import load_dotenv

#create class connection for MYSQL Database
pymysql.connect()
def connect_with_MYSQL(
        sql_user,sql_password,sql_host,sql_database,sql_port):
    """ Connect with MYSQL database"""
    try:
        sql_connection = pymysql.connect(
            user=sql_user,
            password=sql_password,
            database=sql_database,
            host=sql_host,
            port=sql_port
        )
        #check if SQL connection is not implemented
        if sql_connection:
            return sql_connection  #return connection Object
    
        else:
            return None  #return Connection Object
    except MySQLError as e:
        return f" MYSQL Error : {e}"  #return MYSQL internal 
    except Exception as e:
        return f" Connection Failed : {e}"

#create an connection string for MYSQL 

def SQLconnection_with_string(sql_user,sql_password,sql_host,sql_port,sql_database):

    """
    Create SQLAlchemy Engine for MySQL database.
    
    Args:
        sql_user: MySQL username
        sql_password: MySQL password
        sql_host: MySQL host (localhost or IP)
        sql_port: MySQL port (default: 3306)
        sql_database: Database name
        pool_size: Connection pool size (default: 10)
        max_overflow: Maximum overflow connections (default: 20)
        pool_pre_ping: Test connection before using (default: True)
        echo: Log SQL statements (default: False)
    
    Returns:
        SQLAlchemy Engine object or None
    """
    connection_string = (
        f"mysql+pymysql://{sql_user}:{sql_password}@"
        f"{sql_host}:{sql_port}/{sql_database}"
    )
    connection_engine = create_engine(
        url=connection_string,
    )
    return connection_engine

#create an method to execute SQL queries for Cursor Object
def SQL_cursor_object(SQL_connection):

    """ Return cursor connection object to execute SQL queries"""
    Cursor_obj = SQL_connection.cursor()
    return Cursor_obj

#create an method to close cursor object and connection object status close
def close_cursor_obj(Cursor_obj):
    
    return Cursor_obj.close()

def close_SQL_connection(sql_connection):

    return sql_connection.close()
    

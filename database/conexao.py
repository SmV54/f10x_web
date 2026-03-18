import psycopg2


def conectar():

    conn = psycopg2.connect(
        host="db.yxberbwwchmikvzgbtqh.supabase.co",
        database="postgres",
        user="postgres",
        password="SmV#1954",
        port="5432"
    )

    return conn
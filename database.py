import pymysql
import config

def get_db_connection():
    """Opretter og returnerer en forbindelse til databasen ved hjælp af konfigurationsindstillinger."""
    return pymysql.connect(
        host=config.DB_HOST,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        database=config.DB_NAME
    )

def test_db_connection():
    """Tester forbindelsen til databasen og udskriver en succes- eller fejlmeddelelse."""
    connection = None
    try:
        connection = get_db_connection()
        print("Database connection successful")
    except pymysql.MySQLError as e:
        print(f"An error occurred while connecting to the database: {e}")
    finally:
        if connection:
            connection.close()

def fetch_data():
    """Henter data fra en tabel og udskriver resultaterne."""
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            sql = "SELECT * FROM unban_requests"  # Erstat 'din_tabel' med din faktiske tabelnavn
            cursor.execute(sql)
            result = cursor.fetchall()
            print(result)
    except pymysql.MySQLError as e:
        print(f"An error occurred while fetching data: {e}")
    finally:
        if connection:
            connection.close()

def get_request_count(steamid):
    """Henter antallet af anmodninger for et givet steamid."""
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            sql = """
            SELECT request_count FROM unban_requests
            WHERE steamid = %s
            """
            cursor.execute(sql, (steamid,))
            result = cursor.fetchone()
            return result[0] if result else 0
    except pymysql.MySQLError as e:
        print(f"An error occurred while getting request count: {e}")
        return 0
    finally:
        if connection:
            connection.close()

def reset_request_counts_older_than(days=7):
    """Nulstiller request_count for brugere, der ikke har sendt en anmodning i de sidste 'days' dage."""
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            sql = """
            UPDATE unban_requests
            SET request_count = 0
            WHERE request_time < NOW() - INTERVAL %s DAY
            """
            cursor.execute(sql, (days,))
            connection.commit()
            print(f"Request counts reset for requests older than {days} days.")
    except pymysql.MySQLError as e:
        print(f"An error occurred while resetting request counts: {e}")
    finally:
        if connection:
            connection.close()

def add_or_update_unban_request(steamid, faceit_nickname, hub, reason, max_requests=3):
    """Tilføjer eller opdaterer en unban-anmodning. Nægter yderligere anmodninger, hvis grænsen er nået."""
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # Kontroller antallet af eksisterende anmodninger
            current_count = get_request_count(steamid)
            
            if current_count >= max_requests:
                print("Max request limit reached. Cannot add new request.")
                return False

            # Først prøv at opdatere eksisterende anmodning
            update_sql = """
            UPDATE unban_requests
            SET faceit_nickname = %s, hub = %s, reason = %s, request_count = request_count + 1, request_time = CURRENT_TIMESTAMP
            WHERE steamid = %s
            """
            cursor.execute(update_sql, (faceit_nickname, hub, reason, steamid))
            
            # Hvis ingen rækker blev opdateret, indsæt en ny
            if cursor.rowcount == 0:
                insert_sql = """
                INSERT INTO unban_requests (steamid, faceit_nickname, hub, reason, request_count, request_time, bans)
                VALUES (%s, %s, %s, %s, 1, CURRENT_TIMESTAMP, NULL)
                """
                cursor.execute(insert_sql, (steamid, faceit_nickname, hub, reason))
            
            connection.commit()
            return True
    except pymysql.MySQLError as e:
        print(f"An error occurred while adding or updating unban request: {e}")
        return False
    finally:
        if connection:
            connection.close()




def check_existing_request(steamid, faceit_nickname):
    """Kontrollerer, om en unban-anmodning med det givne steamid og faceit_nickname allerede findes."""
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            sql = """
            SELECT request_count FROM unban_requests
            WHERE steamid = %s AND faceit_nickname = %s
            """
            cursor.execute(sql, (steamid, faceit_nickname))
            result = cursor.fetchone()
            return result[0] if result else 0
    except pymysql.MySQLError as e:
        print(f"An error occurred while checking existing request: {e}")
        return 0
    finally:
        if connection:
            connection.close()

# Test database connection
test_db_connection()


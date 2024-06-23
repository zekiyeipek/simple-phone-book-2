from flask import Flask, render_template, request, redirect, url_for, session
import cx_Oracle

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with an actual secret key for session security

oracle_connection = cx_Oracle.connect("SYS/123@XE", mode=cx_Oracle.SYSDBA)
cursor = oracle_connection.cursor()

create_user_table_sql = """
CREATE TABLE user_logins (
    id NUMBER PRIMARY KEY,
    username VARCHAR2(50) NOT NULL,
    password VARCHAR2(50) NOT NULL
)
"""
    
create_person_table_sql = """
CREATE TABLE people (
    id NUMBER PRIMARY KEY,
    name VARCHAR2(100) NOT NULL,
    phone_number VARCHAR2(20) NOT NULL,
    photo_url VARCHAR2(255),
    user_id NUMBER REFERENCES user_logins(id) NOT NULL
)
"""

create_sequence_sql = "CREATE SEQUENCE people_seq START WITH 1 INCREMENT BY 1"

# Check if the sequence already exists before creating it
cursor.execute("SELECT sequence_name FROM user_sequences WHERE sequence_name = 'PEOPLE_SEQ'")
existing_sequence = cursor.fetchone()

if not existing_sequence:
    cursor.execute(create_sequence_sql)


# Sample data for testing (replace with actual data)
sample_users_data = [
    (1, 'user1', 'password1'),
    (2, 'user2', 'password2'),
]

sample_people_data = [
    {'name': 'John Doe', 'phone': '123-456-7890', 'photo_url': 'john.jpg', 'user_id': 1},
    {'name': 'Jane Doe', 'phone': '987-654-3210', 'photo_url': 'jane.jpg', 'user_id': 2},
]

# Function to check if a table exists
def table_exists(table_name):
    cursor.execute("SELECT table_name FROM user_tables WHERE table_name = :1", (table_name,))
    return cursor.fetchone() is not None

if not table_exists('USER_LOGINS'):
    cursor.execute(create_user_table_sql)

# Check if the user_logins table is empty before inserting sample data
cursor.execute("SELECT COUNT(*) FROM user_logins")
user_logins_count = cursor.fetchone()[0]

if user_logins_count == 0:
    # Insert sample user data only if the user_logins table is empty
    cursor.executemany("INSERT INTO user_logins VALUES (:1, :2, :3)", sample_users_data)

# Initialize database tables and data for people
if not table_exists('PEOPLE'):
    cursor.execute(create_person_table_sql)

# Insert sample data into the people table
cursor.executemany("INSERT INTO people VALUES (people_seq.NEXTVAL, :name, :phone, :photo_url, :user_id)", sample_people_data)
oracle_connection.commit()

@app.route('/')
def index():
    return redirect(url_for('login'))

# Sample route for login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Implement user authentication logic (replace with actual authentication)
        cursor.execute("SELECT * FROM user_logins WHERE username = :1 AND password = :2", (username, password))
        user = cursor.fetchone()

        if user:
            session['user_authenticated'] = True
            print("User authenticated. Redirecting to main.")
            return redirect(url_for('main'))
        else:
            print("Authentication failed. User not found.")

    return render_template('login.html')

# Sample route for the main screen
@app.route('/main', methods=['GET', 'POST'])
def main():
    # Check if the user is authenticated
    if not session.get('user_authenticated'):
        return redirect(url_for('login'))

    if request.method == 'POST':
        # Handle form submission if needed
        pass

    # Fetch data from the database based on search query
    search_query = request.args.get('search', '')
    if search_query:
        # Perform a database query with the search criteria
        query = "SELECT * FROM people WHERE LOWER(name) LIKE LOWER(:1)"
        cursor.execute(query, ('%' + search_query + '%',))
        
    else:
        # Fetch all data if no search query
        cursor.execute("SELECT * FROM people")
        
    # Fetch the results with the photo_url field
    columns = [col[0] for col in cursor.description]
    people_data = [dict(zip(columns, row)) for row in cursor.fetchall()]

    return render_template('main.html', people=people_data, search_query=search_query)


# Sample route for adding a new person
@app.route('/add_person', methods=['GET', 'POST'])
def add_person():
    if request.method == 'POST':
        name = request.form['name']
        phone = request.form['phone']

        # Fetch the next value from the sequence
        cursor.execute("SELECT people_seq.NEXTVAL FROM dual")
        next_id = cursor.fetchone()[0]

        # Insert the new person with the fetched ID
        cursor.execute("""
            INSERT INTO people (id, name, phone_number, user_id)
            VALUES (:id, :name, :phone, :user_id)
        """, {'id': next_id, 'name': name, 'phone': phone, 'user_id': 1})  # Replace '1' with the actual user ID
        
        oracle_connection.commit()

        return redirect(url_for('main'))

    return render_template('add_person.html')

# Sample route for editing or removing a person
@app.route('/edit_remove_person/<int:person_id>', methods=['GET', 'POST'])
def edit_remove_person(person_id):
    # Fetch person data from the database based on person_id
    cursor.execute("SELECT * FROM people WHERE id = :1", (person_id,))
    person_data = cursor.fetchone()

    if request.method == 'POST':
        name = request.form['name']
        phone = request.form['phone']

        # Update the person's information in the database
        cursor.execute("UPDATE people SET name = :1, phone_number = :2 WHERE id = :3", (name, phone, person_id))
        oracle_connection.commit()
        return redirect(url_for('main'))

    return render_template('edit_remove_person.html', person=person_data)

@app.route('/remove_person/<int:person_id>', methods=['POST'])
def remove_person(person_id):
    cursor.execute("DELETE FROM people WHERE id = :1", (person_id,))
    oracle_connection.commit()
    return redirect(url_for('main'))

if __name__ == '__main__':
    app.run(debug=True)

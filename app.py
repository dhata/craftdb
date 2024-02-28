import os
import psycopg2
from psycopg2 import extras
from datetime import datetime, timezone
from dotenv import load_dotenv
from flask import Flask, request, url_for, render_template, jsonify

SUBQ_TOTAL_COST_BY_PROJECT_ID= '''select t.project_id, sum(t.total_cost) as total_cost from (select usages.usage_id, usages.project_id, usages.units, supplies.cost/supplies.volume as costper, supplies.cost/supplies.volume*usages.units as total_cost from usages left join supplies on supplies.supply_id = usages.supply_id) t group by project_id'''
CREATE_ROOMS_TABLE = (
    "CREATE TABLE IF NOT EXISTS rooms (id SERIAL PRIMARY KEY, name TEXT);"
)
CREATE_TEMPS_TABLE = """CREATE TABLE IF NOT EXISTS temperatures (room_id INTEGER, temperature REAL, 
                        date TIMESTAMP, FOREIGN KEY(room_id) REFERENCES rooms(id) ON DELETE CASCADE);"""
CREATE_PROJECTS_TABLE = (
    "CREATE TABLE IF NOT EXISTS projects (project_id SERIAL PRIMARY KEY, name TEXT, date TIMESTAMP, type TEXT);"
)
CREATE_SUPPLIES_TABLE = (
    "CREATE TABLE IF NOT EXISTS supplies (supply_id SERIAL PRIMARY KEY, name TEXT, purchase_date TIMESTAMP, brand TEXT, store TEXT, volume INTEGER, cost FLOAT, estimate BOOLEAN, used BOOLEAN, multipack_id INTEGER, FOREIGN KEY (multipack_id) REFERENCES multipacks(multipack_id));"
)
CREATE_MULTIPACKS_TABLE = (
    "CREATE TABLE IF NOT EXISTS multipacks (multipack_id SERIAL PRIMARY KEY, name TEXT, purchase_date TIMESTAMP, brand TEXT, store TEXT, volume INTEGER, cost FLOAT );"
)
CREATE_USAGES_TABLE = (
    "CREATE TABLE IF NOT EXISTS usages (usage_id SERIAL PRIMARY KEY, project_id INTEGER, supply_id INTEGER, units INTEGER, FOREIGN KEY(project_id) REFERENCES projects(project_id), FOREIGN KEY(supply_id) REFERENCES supplies(supply_id) );"
)

INSERT_ROOM_RETURN_ID = "INSERT INTO rooms (name) VALUES (%s) RETURNING id;"
INSERT_PROJECTS_RETURN_ID = "INSERT INTO projects (name, date, type) VALUES (%s, %s, %s) RETURNING project_id;"
INSERT_TEMP = (
    "INSERT INTO temperatures (room_id, temperature, date) VALUES (%s, %s, %s);"
)
INSERT_SUPPLIES_RETURN_ID = (
    "INSERT INTO supplies (name, purchase_date, brand, store, volume, cost, estimate, used, multipack_id ) VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING supply_id;"
)
INSERT_MULTIPACKS_RETURN_ID = (
    "INSERT INTO multipacks (name, purchase_date, brand, store, volume, cost ) VALUES(%s, %s, %s, %s, %s, %s) RETURNING multipack_id;"
)
INSERT_USAGES_RETURN_ID = (
    "INSERT INTO usages (project_id, supply_id, units ) VALUES %s RETURNING usage_id;"
)

DELETE_USAGES_RETURN_ID = (
    "DELETE FROM usages WHERE (project_id, supply_id ) in (%s) RETURNING usage_id;"
)

UPDATE_PROJECTS_RETURN_ID = """UPDATE projects SET name='{name}', date='{date}', type='{type}', notes='{notes}' WHERE project_id = {project_id} RETURNING project_id"""
UPDATE_MULTIPACKS_RETURN_ID = """UPDATE multipacks SET name='{name}', purchase_date='{purchase_date}', brand='{brand}', store='{store}', volume='{volume}', cost='{cost}' WHERE multipack_id = {multipack_id} RETURNING multipack_id"""
UPDATE_SUPPLIES_RETURN_ID = """UPDATE supplies SET name='{name}', purchase_date='{purchase_date}', brand='{brand}', store='{store}', volume='{volume}', cost='{cost}', estimate='{estimate}', used='{used}' WHERE supply_id = {supply_id} RETURNING supply_id"""
UPDATE_USAGES_RETURN_ID = """UPDATE usages u SET units = v.units, notes = v.notes FROM (values {0} ) AS v (usage_id, units, notes) WHERE v.usage_id = u.usage_id RETURNING u.usage_id;"""

FETCH_PROJECTS = """SELECT projects.project_id, projects.name, projects.date, projects.type, coalesce(s.total_cost,0) as total_cost FROM projects left join ("""+SUBQ_TOTAL_COST_BY_PROJECT_ID+""") s on s.project_id = projects.project_id ORDER BY projects.project_id;"""
FETCH_MULTIPACKS = """SELECT * FROM multipacks;"""
FETCH_SUPPLIES = """SELECT supplies.*, supplies.cost/supplies.volume as costper, usages.usage_count FROM supplies left join (SELECT supply_id, SUM(units) AS usage_count FROM usages GROUP BY supply_id) usages ON supplies.supply_id = usages.supply_id ORDER BY supplies.supply_id;"""
FETCH_PROJECT_TYPES = """SELECT DISTINCT type FROM projects;"""
FETCH_BRANDS = """SELECT DISTINCT brand FROM (
    SELECT brand FROM multipacks 
    UNION 
    SELECT brand FROM supplies
    ) t"""
FETCH_STORES = """SELECT DISTINCT store FROM (
    SELECT store FROM multipacks 
    UNION 
    SELECT store FROM supplies
    ) t"""


CHECK_PROJECT = """SELECT * FROM projects LIMIT 0"""
CHECK_MULTIPACK = """SELECT * FROM multipacks LIMIT 0"""
CHECK_SUPPLY = """SELECT supply_id, name, purchase_date, brand, store, volume, cost, estimate FROM supplies LIMIT 0"""

GET_PROJECT = """SELECT projects.*, coalesce(s.total_cost,0)::numeric::money as total_cost FROM projects left join ("""+SUBQ_TOTAL_COST_BY_PROJECT_ID+""") s on s.project_id = projects.project_id WHERE projects.project_id = {0} LIMIT 1 """
GET_MULTIPACK = """SELECT * FROM multipacks WHERE multipack_id = {0} LIMIT 1 """
GET_SUPPLY = """SELECT * FROM supplies WHERE supply_id = {0} LIMIT 1 """
GET_SUPPLY_FROM_MULTIPACK = """SELECT * FROM supplies WHERE multipack_id = {0}"""
GET_SUPPLIES_WITH_USAGE_FROM_PROJECT = """
    SELECT supplies.supply_id, supplies.name, supplies.purchase_date, supplies.brand, supplies.store, supplies.volume, supplies.cost, supplies.cost/supplies.volume as costper, usages.usage_id is not null as included FROM supplies 
    LEFT JOIN (
        SELECT * FROM usages WHERE usages.project_id = {0}) usages
    ON supplies.supply_id = usages.supply_id
    WHERE supplies.used IS NOT True"""
GET_USAGES_FROM_PROJECT = """
    SELECT usages.usage_id, supplies.name, supplies.brand, supplies.volume, supplies.cost, supplies.cost/supplies.volume as costper, usages.units, supplies.cost/supplies.volume*usages.units as total_cost, usages.notes FROM supplies 
    JOIN (
        SELECT * FROM usages WHERE usages.project_id = {0}) usages
    ON supplies.supply_id = usages.supply_id
    WHERE supplies.used IS NOT True"""

GLOBAL_NUMBER_OF_DAYS = (
    """SELECT COUNT(DISTINCT DATE(date)) AS days FROM temperatures;"""
)
GLOBAL_AVG = """SELECT AVG(temperature) as average FROM temperatures;"""

DROP_SUPPLIES = """DROP TABLE supplies"""
DROP_USAGES = """DROP TABLE usages"""
DROP_PROJECTS = """DROP TABLE projects"""
DROP_MULTIPACKS = """DROP TABLE multipacks"""

GET_TOTAL_ENTRIES = """Select (select count(*) from projects) as Count1, (select count(*) from multipacks) as Count2, (select count(*) from supplies) as Count3, (select count(*) from usages) as Count4"""

# reads the variables from .env
load_dotenv()

app = Flask(__name__)
url = os.getenv("DATABASE_URL")
connection = psycopg2.connect(url)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/view/<object>", methods=['GET'])
def view(object):
    query = ""
    title = ""
    if object=='project':
        query = FETCH_PROJECTS
        title = "View Projects"
    elif object == 'multipack':
        query = FETCH_MULTIPACKS
        title = "View Multipacks"
    elif object == 'supply':
        query = FETCH_SUPPLIES
        title = "View Supplies"
    with connection:
        with connection.cursor() as cursor:
            cursor.execute(query)
            data = cursor.fetchall()
            fields = [i[0] for i in cursor.description]
    return render_template("view.html", object=object, fields=fields, data=data, title = title)

@app.route("/create/<object>",methods=['GET','POST'])
def create(object):
    data = []
    query = ""
    dropdown = {}
    dropdown.update(get_project_types()[0])
    dropdown.update(get_brands()[0])
    dropdown.update(get_stores()[0])
    if object=="project":
        print("project object")
        query = CHECK_PROJECT
    elif object == "multipack":
        query = CHECK_MULTIPACK
    elif object == "supply":
        query = CHECK_SUPPLY
    with connection:
         with connection.cursor() as cursor:
            cursor.execute(query)
    print(cursor.description)
    keyword = "New"
    data = list([(desc.name, None , desc.type_code) for desc in cursor.description])
    if request.method == 'POST':
        if object == "supply":
            print(request.form)
            print(data)
            data.append(('multipack_id',request.form['multipack_id'],23))
            data.pop(2)
            data.insert(2,('purchase_date', request.form['purchase_date'],1114))
            data.pop(3)
            data.insert(3,('brand', request.form['brand'],25))
            data.pop(4)
            data.insert(4,('store', request.form['store'],25))
            data.pop(6)
            data.insert(6,('cost', request.form['costper'],701))
            keyword = "FromMultipack"
    print(data)
    return render_template("edit.html", object=object, data = data, dropdown=dropdown, keyword = keyword)


@app.route("/edit/<object>/<objectid>")
def edit(object, objectid):
    print(object)
    data = []
    query = ""
    dropdown = {}
    dropdown.update(get_project_types()[0])
    dropdown.update(get_brands()[0])
    dropdown.update(get_stores()[0])
    print(objectid)
    if object=="project":
        print("project object")
        query = GET_PROJECT
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(query.format(objectid))
                data = list(([((cursor.description[i][0], value, cursor.description[i][1]) \
                    for i, value in enumerate(row)) for row in cursor.fetchall()])[0])
        
        print(data)
        print(dropdown)
        query = GET_USAGES_FROM_PROJECT
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(query.format(objectid))
                childdata = cursor.fetchall()
                childfields = [i[0] for i in cursor.description]
                print([i for i in cursor.description])
        return render_template("project.html", object= object, data=data, dropdown=dropdown, keyword="Edit", childdata=childdata, childfields=childfields)
    elif object == "multipack":
        query = GET_MULTIPACK
        with connection:
         with connection.cursor() as cursor:
            cursor.execute(query.format(objectid))
            data = list(([((cursor.description[i][0], value, cursor.description[i][1]) \
                for i, value in enumerate(row)) for row in cursor.fetchall()])[0])
        
        query = GET_SUPPLY_FROM_MULTIPACK
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(query.format(objectid))
                childdata = cursor.fetchall()
                childfields = [i[0] for i in cursor.description]
        
        return render_template("multipack.html", object= object, data=data, dropdown=dropdown, keyword="Edit", childdata=childdata, childfields=childfields)
    elif object == "supply":
        query = GET_SUPPLY
    with connection:
         with connection.cursor() as cursor:
            cursor.execute(query.format(objectid))
            data = list(([((cursor.description[i][0], value, cursor.description[i][1]) \
                for i, value in enumerate(row)) for row in cursor.fetchall()])[0])
    print(data)
    print(dropdown)
    return render_template("edit.html", object= object, data=data, dropdown=dropdown, keyword = "Edit")

# @app.route('/item/<int:appitemid>/')
# @app.route('/item/<int:appitemid>/<path:anythingcanbehere>')
@app.route("/view/usage/<project_id>", methods=["POST"])
def view_usage(project_id):
    query = GET_SUPPLIES_WITH_USAGE_FROM_PROJECT
    with connection:
         with connection.cursor() as cursor:
            cursor.execute(query.format(project_id))
            data = cursor.fetchall()
            fields = [i[0] for i in cursor.description]
            # data = list(([((cursor.description[i][0], value, cursor.description[i][1]) \
            #     for i, value in enumerate(row)) for row in cursor.fetchall()])[0])
    print(data)
    return render_template("checklist.html", object = 'supply', fields = fields, data = data, project_id = project_id, link = False)

@app.post("/api/room")
def create_room():
    data = request.get_json()
    name = data["name"]
    with connection:
        with connection.cursor() as cursor:
            cursor.execute(CREATE_ROOMS_TABLE)
            cursor.execute(INSERT_ROOM_RETURN_ID,(name,))
            room_id = cursor.fetchone()[0]
    return {"id": room_id, "message": f"Room {name} created."}, 201

@app.post("/api/project")
def create_project():
    data = request.get_json()
    name = data["name"]
    type = data["type"]
    try:
        date = datetime.strptime(data["date"],"%m/%d/%Y")
    except KeyError:
        date = datetime.now(timezone.utc)

    with connection:
        with connection.cursor() as cursor:
            cursor.execute(CREATE_PROJECTS_TABLE)
            cursor.execute(INSERT_PROJECTS_RETURN_ID,(name, date, type))
            project_id = cursor.fetchone()[0]
    return {"id": project_id, "message": f"Project {name} created.", "redirect":"/edit/project/"+str(project_id)}, 201

@app.post("/api/supply")
def create_supply():
    data = request.get_json()
    name = data["name"]
    brand = data["brand"]
    store = data["store"]
    volume = data["volume"]
    cost = data["cost"]
    estimate = data["estimate"]
    used = data.get("used",False)
    multipack_id = data.get("multipack_id")
    print("create supply")
    print(data)
    try:
        purchase_date = datetime.strptime(data["purchase_date"],"%m/%d/%Y")
    except KeyError:
        purchase_date = datetime.now(timezone.utc)

    with connection:
        with connection.cursor() as cursor:
            cursor.execute(CREATE_SUPPLIES_TABLE)
            cursor.execute(INSERT_SUPPLIES_RETURN_ID,(name, purchase_date, brand, store, volume, cost, estimate, used, multipack_id))
            supply_id = cursor.fetchone()[0]
    return {"id": supply_id, "message": f"Supply {name} created.", "redirect":"/edit/supply/"+str(supply_id)}, 201

@app.post("/api/multipack")
def create_multipack():
    data = request.get_json()
    name = data["name"]
    brand = data["brand"]
    store = data["store"]
    volume = data["volume"]
    cost = data["cost"]
    try:
        purchase_date = datetime.strptime(data["purchase_date"],"%m/%d/%Y")
    except KeyError:
        purchase_date = datetime.now(timezone.utc)

    with connection:
        with connection.cursor() as cursor:
            cursor.execute(CREATE_MULTIPACKS_TABLE)
            cursor.execute(INSERT_MULTIPACKS_RETURN_ID,(name, purchase_date, brand, store, volume, cost))
            multipack_id = cursor.fetchone()[0]
    return {"id": multipack_id, "message": f"Multipack {name} created.", "redirect":"/edit/multipack/"+str(multipack_id)}, 201


@app.post("/api/usage")
def create_delete_usage():
    data = request.get_json()
    print(data)
    project_id = data["project_id"]
    supply_ids = data["supply_ids"] # list of ids
    volume = 0
    with connection:
        with connection.cursor() as cursor:
            cursor.execute(CREATE_USAGES_TABLE)
    new_values = [(supply_id, i, n) for supply_id, i, n in zip(data["supply_ids"], data["initial_usages"],data['new_usages']) if i != n]
    # this is a list of tuples (supply_id, i, n) need to compare values
    print(new_values)
    add = []
    remove = []
    [add.append((project_id, v[0],0 )) if v[2]>v[1] else remove.append((project_id, v[0])) for v in new_values]
    # want to return a list of tuples: [(1,2,0),(1,3,0)]
    print(add)
    print(remove)
    with connection:
        with connection.cursor() as cursor:
            psycopg2.extras.execute_values(cursor,INSERT_USAGES_RETURN_ID, add)
            psycopg2.extras.execute_values(cursor,DELETE_USAGES_RETURN_ID, remove)
            usage_ids = [i for row in cursor.fetchall() for i in row ]
    return {"id": usage_ids, "message": f"Supply IDs {', '.join([str(s[1]) for s in add])} added to Project ID {project_id}"}

@app.post("/api/project/update")
def update_project():
    data = request.get_json()
    with connection:
        with connection.cursor() as cursor:
            print(data)
            cursor.execute(UPDATE_PROJECTS_RETURN_ID.format(**data))
            id = cursor.fetchone()[0]
    return {"id": id, "message": f"Project {data['name']} updated.", "redirect":"/edit/project/"+str(id)}, 201

@app.post("/api/multipack/update")
def update_multipack():
    data = request.get_json()
    print(data)
    with connection:
        with connection.cursor() as cursor:
            cursor.execute(UPDATE_MULTIPACKS_RETURN_ID.format(**data))
            id = cursor.fetchone()[0]
    return {"id": id, "message": f"Multipack {data['name']} updated.", "redirect":"/edit/multipack/"+str(id)}, 201

@app.post("/api/supply/update")
def update_supply():
    data = request.get_json()
    with connection:
        with connection.cursor() as cursor:
            cursor.execute(UPDATE_SUPPLIES_RETURN_ID.format(**data))
            id = cursor.fetchone()[0]
    return {"id": id, "message": f"Supply {data['name']} updated.", "redirect":"/edit/supply/"+str(id)}, 201

@app.post("/api/usage/update")
def update_usage():
    print('update usage')
    data = request.get_json()
    print(data)
    values =", ".join(["("+ obj['usage_id']+", "+obj['units']+", '"+obj['notes']+"')" for obj in data.values()])
    
    print(values)
    with connection:
        with connection.cursor() as cursor:
            cursor.execute(UPDATE_USAGES_RETURN_ID.format(values))
            ids = [ row[0] for row in cursor.fetchall()]
    return {"id:": ids, "message": f"Usages Updated. Refresh page to recalculate"}, 201

@app.post("/api/drop_supplies")
def drop_supplies():
    with connection:
        with connection.cursor() as cursor:
            cursor.execute(DROP_SUPPLIES)
    return {"message": f"Supplies Table Dropped"}, 201

@app.post("/api/drop_usages")
def drop_usages():
    with connection:
        with connection.cursor() as cursor:
            cursor.execute(DROP_USAGES)
    return {"message": f"Usages Table Dropped"}, 201

@app.post("/api/drop_projects")
def drop_projects():
    with connection:
        with connection.cursor() as cursor:
            cursor.execute(DROP_PROJECTS)
    return {"message": f"Projects Table Dropped"}, 201

@app.post("/api/drop_multipacks")
def drop_multipacks():
    with connection:
        with connection.cursor() as cursor:
            cursor.execute(DROP_MULTIPACKS)
    return {"message": f"Multipacks Table Dropped"}, 201

@app.post("/api/temperature")
def add_temp():
    data = request.get_json()
    temperature = data["temperature"]
    room_id = data["room"]
    try:
        date = datetime.strptime(data["date"],"%m-%d-%Y %H:%M:%S")
    except KeyError:
        date = datetime.now(timezone.utc)

    with connection:
        with connection.cursor() as cursor:
            cursor.execute(CREATE_TEMPS_TABLE)
            cursor.execute(INSERT_TEMP,(room_id, temperature, date))
    return {"message": "Temperature added."}, 201

@app.get("/api/average")
def get_global_avg():
    with connection:
        with connection.cursor() as cursor:
            cursor.execute(GLOBAL_AVG)
            average = cursor.fetchone()[0]
            cursor.execute(GLOBAL_NUMBER_OF_DAYS)
            days = cursor.fetchone()[0]
    return {"average": round(average,2), "days": days}

@app.get("/api/projectTypes")
def get_project_types():
    with connection:
        with connection.cursor() as cursor:
            cursor.execute(FETCH_PROJECT_TYPES)
            types = [i for row in cursor.fetchall() for i in row ]
    return {"type": types}, 201

@app.get("/api/brands")
def get_brands():
    with connection:
        with connection.cursor() as cursor:
            cursor.execute(FETCH_BRANDS)
            brands = [i for row in cursor.fetchall() for i in row ]
    return {"brand": brands}, 201

@app.get("/api/stores")
def get_stores():
    with connection:
        with connection.cursor() as cursor:
            cursor.execute(FETCH_STORES)
            stores = [i for row in cursor.fetchall() for i in row ]
    return {"store": stores}, 201

@app.get("/api/totalEntries")
def get_total_entries():
    with connection:
        with connection.cursor() as cursor:
            cursor.execute(GET_TOTAL_ENTRIES)
            totals = [i for row in cursor.fetchall() for i in row ]
    return {"Table Entries": totals, "Total": sum(totals)}, 201

@app.template_filter("prettyname")
def prettyname(name):
    pretty_name = name.title()
    pretty_name = pretty_name.replace("_", " ")
    if pretty_name== "Id":
        pretty_name = "#"
    elif pretty_name== "Used":
        pretty_name = "Used Up"
    return pretty_name

@app.template_filter("prettyvalue")
def prettyvalue(value):
    if isinstance(value,datetime):
        return value.strftime('%m/%d/%Y')
    elif isinstance(value,float):
        return ('${:0,.2f}').format(value)
    elif value is None:
        return ""
    elif value == True and type(value)!=int:
        return """<div class="form-check form-switch text-center">
        <input class = "form-check-input" checked type="checkbox" ></div>"""
    elif value == False and type(value)!=int:
        return """<div class="form-check form-switch text-center">
        <input class = "form-check-input" type="checkbox" ></div>"""
    else:
        return value
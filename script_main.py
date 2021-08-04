import sqlite3
import ipaddress
import datetime
import argparse
import configparser
from os import walk
from os import system


# Initialize parser
parser = argparse.ArgumentParser()

# Adding optional argument

parser.add_argument("-c", "--config", dest="config", type=str,
                    help="give config file (python configparser file *.ini format)")

parser.add_argument("-c_db", "--create_db", dest="create_db", required=False,
                    help="if you dont have an existing sqlite3 database. create sqlite3 database with powerdns format. name is givin in the config file", action="store_true")

parser.add_argument("-add_z", "--add_zone_files", required=False,  dest="add_zone_files",
                    help="if you want to fill an empty database with zone file records. path to bind zone file directory is in the config file", action="store_true")

parser.add_argument("-dl", "--domainlist", required=False,  dest="domainlist",
                    help="if you want to update the domain list in the table. path to list of domains in a txt format is given in the config file", action="store_true")


parser.add_argument("-ripv4", "--reverseipv4", dest="ripv4",
                    required=False, help="create all ipv4 PTR records in the database", action="store_true")

parser.add_argument("-ripv6", "--reverseipv6", dest="ripv6",
                    required=False, help="create all ipv6 PTR records in the database", action="store_true")


# Read arguments from command line
args = parser.parse_args()
config_dir = args.config

# read config file
config = configparser.ConfigParser()
config.sections()
config.read(config_dir)

# read name for sqlite3 database
db_name = config['database']['name']

# read path to bind zone files directory
path_zone_files = config['zone']['path_zone_files']

# get file for domain list
domains_list = config['domains']['list_of_domains']


######################################
# create powerdns conform sqlite3 db #
######################################
def gen_sqlite3_db(db_name):
    try:
        conn_db = sqlite3.connect(db_name)
        gen_db = conn_db.cursor()
    except Error as e:
        print(e)
    finally:
        if conn_db:
            gen_db.execute("PRAGMA foreign_keys = 1;")
            gen_db.execute("CREATE TABLE domains (id INTEGER PRIMARY KEY, name VARCHAR(255) NOT NULL COLLATE NOCASE, master VARCHAR(128) DEFAULT NULL, last_check INTEGER DEFAULT NULL, type VARCHAR(6) NOT NULL, notified_serial INTEGER DEFAULT NULL, account VARCHAR(40) DEFAULT NULL);")
            gen_db.execute("CREATE UNIQUE INDEX name_index ON domains(name);")

            gen_db.execute("CREATE TABLE records (id INTEGER PRIMARY KEY, domain_id INTEGER DEFAULT NULL, name VARCHAR(255) DEFAULT NULL, type VARCHAR(10) DEFAULT NULL, content VARCHAR(65535) DEFAULT NULL, ttl INTEGER DEFAULT NULL, prio INTEGER DEFAULT NULL, disabled BOOLEAN DEFAULT 0, ordername VARCHAR(255), auth BOOL DEFAULT 1, FOREIGN KEY(domain_id) REFERENCES domains(id) ON DELETE CASCADE ON UPDATE CASCADE);")
            gen_db.execute(
                "CREATE INDEX records_lookup_idx ON records(name, type);")
            gen_db.execute(
                "CREATE INDEX records_lookup_id_idx ON records(domain_id, name, type);")
            gen_db.execute(
                "CREATE INDEX records_order_idx ON records(domain_id, ordername);")
            gen_db.execute(
                "CREATE TABLE supermasters (ip VARCHAR(64) NOT NULL, nameserver VARCHAR(255) NOT NULL COLLATE NOCASE, account VARCHAR(40) NOT NULL);")
            gen_db.execute(
                "CREATE UNIQUE INDEX ip_nameserver_pk ON supermasters(ip, nameserver);")
            gen_db.execute("CREATE TABLE comments (id INTEGER PRIMARY KEY, domain_id INTEGER NOT NULL, name VARCHAR(255) NOT NULL, type VARCHAR(10) NOT NULL, modified_at INT NOT NULL, account VARCHAR(40) DEFAULT NULL, comment VARCHAR(65535) NOT NULL, FOREIGN KEY(domain_id) REFERENCES domains(id) ON DELETE CASCADE ON UPDATE CASCADE);")
            gen_db.execute(
                "CREATE INDEX comments_idx ON comments(domain_id, name, type);")
            gen_db.execute(
                "CREATE INDEX comments_order_idx ON comments (domain_id, modified_at);")
            gen_db.execute("CREATE TABLE domainmetadata (id INTEGER PRIMARY KEY, domain_id INT NOT NULL, kind VARCHAR(32) COLLATE NOCASE, content TEXT, FOREIGN KEY(domain_id) REFERENCES domains(id) ON DELETE CASCADE ON UPDATE CASCADE);")
            gen_db.execute(
                "CREATE INDEX domainmetaidindex ON domainmetadata(domain_id);")
            gen_db.execute("CREATE TABLE cryptokeys (id INTEGER PRIMARY KEY, domain_id INT NOT NULL, flags INT NOT NULL, active BOOL, published BOOL DEFAULT 1, content TEXT, FOREIGN KEY(domain_id) REFERENCES domains(id) ON DELETE CASCADE ON UPDATE CASCADE);")
            gen_db.execute(
                "CREATE INDEX domainidindex ON cryptokeys(domain_id);")
            gen_db.execute(
                "CREATE TABLE tsigkeys (id INTEGER PRIMARY KEY, name VARCHAR(255) COLLATE NOCASE, algorithm VARCHAR(50) COLLATE NOCASE, secret VARCHAR(255));")
            gen_db.execute(
                "CREATE UNIQUE INDEX namealgoindex ON tsigkeys(name, algorithm);")
            gen_db.execute(
                "ALTER TABLE records ADD COLUMN source VARCHAR(20) DEFAULT NULL;")
            conn_db.close()


####################################
# include or update all zone files #
####################################


def zonefiles2sql(path_zone_files, db_path):
    start = datetime.datetime.now()
    print("\n")
    print("include or update all zone files into database starts...")
    f = []  # list of filenames string for console print
    for (dirpath, dirnames, filenames) in walk(path_zone_files):
        f.extend(filenames)
        break

    for i in range(len(f)):

        command = "zone2sql -gsqlite --zone=" + \
            path_zone_files+"/"+f[i]+" | sqlite3 " + db_path
        print(command)
        system(command)
        print(i)
    end = datetime.datetime.now()
    elapsed = end - start
    print("... finished in", elapsed.seconds, "second(s) and ",
          elapsed.microseconds, "miliseconds")


##################################
# include or update domain table #
##################################


def domain_update(db_path, conn_db):
    start = datetime.datetime.now()
    print("\n")
    print("include or update domain list into database starts...")
    print("Insert or Ignore into database: " + db_path)
    db_domain_update = conn_db.cursor()

    with open(domains_list) as f:
        domains = f.readlines()
    domains = [x.strip() for x in domains]
    print(domains[1])

    for i in range(len(domains)):
        print(domains[i])
        db_domain_update.execute(
            'INSERT OR IGNORE INTO "main"."domains" ("name", "last_check", "type") VALUES (?, "NATIVE", "NATIVE");', (domains[i], ))

    conn_db.commit()
    end = datetime.datetime.now()
    elapsed = end - start
    print("... finished in", elapsed.seconds, "second(s) and ",
          elapsed.microseconds, "miliseconds")




####################################
# domain_id update in records table#
####################################

def domain_id(conn_db):
    db_domain_id = conn_db.cursor()
    db_domain_id_namefor = conn_db.cursor()

    db_domain_id.execute("SELECT id, name From domains;")
    domains = db_domain_id.fetchall()
    domains.sort(key=lambda x: len(domains))

    for name in db_domain_id_namefor.execute("SELECT name FROM records;"):
        for i in range(len(domains)):
            if name[0].endswith(domains[i][1]):
                db_domain_id.execute(
                    "UPDATE records SET domain_id=? WHERE name=?;", (domains[i][0], name[0],))
                break


################
# reverse ipv6 #
################


def reverse_ipv6(conn_db):
    db_AAAA = conn_db.cursor()
    db_AAAA_2 = conn_db.cursor()
    start = datetime.datetime.now()
    print("\n")
    print("Reverse ipv6 starts...")
    i = 0  # counter for double entries
    j = 0  # counter for ptr entries

    db_AAAA_2.execute(
        "SELECT name, content, source FROM records WHERE type='PTR';")
    db_check = db_AAAA_2.fetchall()

    for name, content, source in db_AAAA.execute("SELECT name, content, source FROM records WHERE type='AAAA';"):
        content = ipaddress.IPv6Address(content).reverse_pointer

        pp = False  # permission for including when false, if its true then its already included
        for p in range(len(db_check)-1):
            if content == db_check[p][0]:
                pp = True  # already there
                i += 1
                break

        if pp == False:  # not included -> include
            j += 1
            db_AAAA_2.execute(
                'INSERT INTO records ("name", "type", "content", "source") VALUES (?, "PTR", ?, ?);', (content, name, source,))

    end = datetime.datetime.now()
    elapsed = end - start
    print(j, "IPv6 PTR entries created and ", i, " already existing PTR entries - finished in", elapsed.seconds, "second(s) and ",
          elapsed.microseconds, "miliseconds")

################
# reverse ipv4 #
################


def reverse_ipv4(conn_db):

    print("\n")
    print("Reverse ipv4 starts...")
    start = datetime.datetime.now()
    db_A = conn_db.cursor()
    db_A_2 = conn_db.cursor()
    i = 0
    j = 0

    db_A_2.execute(
        "SELECT name, content, source FROM records WHERE type='PTR';")
    db_check = db_A_2.fetchall()

    for name, content, source in db_A.execute("SELECT name, content, source FROM records WHERE type='A';"):
        content = ipaddress.IPv4Address(content).reverse_pointer

        pp = False  # permission for including when false, if its true then its already included
        for p in range(len(db_check)-1):
            if content == db_check[p][0]:
                pp = True  # already there
                i += 1
                break

        if pp == False:  # not included -> include
            j += 1
            db_A_2.execute(
                'INSERT INTO records ("name", "type", "content", "source") VALUES (?, "PTR", ?, ?);', (content, name, source,))

    end = datetime.datetime.now()
    elapsed = end - start
    print(j, "IPv4 PTR entries created -  finished in", elapsed.seconds, "second(s) and ",
          elapsed.microseconds, "miliseconds with", i, "x ipv4 double entries \n")


###################
# commit database #
###################

def CommitAndClose(conn_db):
    try:
        conn_db.commit()
        print("Changes are commited succesfully!")
    except:
        print("Changes are NOT commited succesfuly!")

    try:
        conn_db.close()
        print("Connection to database is closed succesfully!")
    except:
        print("Connection to Database could not closed succesfully!")


#################
# Main function #
#################
if __name__ == "__main__":

    start_total = datetime.datetime.now()

    # create sqlite3 database if argument is used
    if args.create_db:
        gen_sqlite3_db(db_name)

    # start connection to sqlite3 database
    try:
        conn_db = sqlite3.connect(db_name)
        print('Database Connection successful!')
    except:
        print("Connection to Sqlite database NOT successful!")

    db = conn_db.cursor()

    # update list of domain table, if argument is used
    if args.domainlist:
        try:
            db.execute("DELETE FROM domains;")
            print("Clearing domains table successful")
        except:
            print("Clearing domains table NOT successful!")
        domain_update(db_name, conn_db)

    # add BIND zone files if argument is used
    if args.add_zone_files:
        # close connection to database before starting zonefiles2sql function, otherwise it doesnt work
        CommitAndClose(conn_db)

        zonefiles2sql(path_zone_files, db_name)

        # restart connection to database
        print("\n")
        try:
            conn_db = sqlite3.connect(db_name)
            print('Database Connection successful!')
        except:
            print("Connection to Sqlite database NOT successful!")


    if args.ripv6:
        reverse_ipv6(conn_db)

    if args.ripv4:
        reverse_ipv4(conn_db)

    # if anything is added into the records table, the id of that record must be updated
    if args.idoit or args.ripv6 or args.ripv4:
        domain_id(conn_db)

    CommitAndClose(conn_db)

    end_total = datetime.datetime.now()
    elapsed_total = end_total - start_total
    print("Finished in total time: ", elapsed_total.seconds, "second(s) and ",
          elapsed_total.microseconds/1000, "milliseconds")

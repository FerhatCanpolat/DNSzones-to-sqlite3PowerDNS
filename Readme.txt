################################
#### Examples for execuation####
################################

#	python3 script_main.py -c config.ini -c_db
The script creates a sqlite3 database with the format required by PowerDNS. The name of the database is in the config.ini

#	python3 script_main.py -c config.ini  -dl -ripv4 -ripv6
The script is called with the config.ini. The domain list is being updated. For ipv4 and ipv6 entries an PTR entry will be created and included into the database.



#######################
####  7 Parameter  ####
#######################

-c		Information for config.ini
			The config.ini has four entries
			[database]  
				- if a database already exists, this should be specified here; it is advisable to store it in the same folder.
				- if there is no database, enter the desired name
				- how to declare in the config:
					name = NameDerDatenbank.db	
				
			[zone]
				- declaration on the folder in which the BIND zone files are located
				- how to declare in the config:
					path_zone_files = File
			[domains]
				- declaration about a txt file. This txt file contains domain names, line by line.
					- example: 
						example.com
						example.net
						...
				- how to declare in the config:
					list_of_domains = DomainTxtFile.txt	


-c_db		f no sqlite3 database exists, this script uses this argument to create an empty sqlite3 database with the format requested by PowerDNS. The name for the database is entered in the config.ini under the section [database]

-add_z		Updates or adds the entries of the BIND zone files to a database. The path to the BIND zone files is given in the config.ini under [zone]

-dl			When the list of domain names in the database should be updated. The path to the txt file with the domain list is given in the config.ini under [domains]. The list is deleted from the database and completely replaced with the one in the txt file.

-ripv4		Creates the required PTR entries of the ipv4 addresses in the database. The method looks for all ipv4 entries and inserts the already non-existent reverse entry of the address into the database. In doing so, it checks whether this PTR entry already exists.

-ripv6		Creates the required PTR entries of the ipv6 addresses in the database. The method looks for all ipv6 entries and inserts the already non-existent reverse entry of the address into the database. In doing so, it checks whether this PTR entry already exists.



##################
#### methods ####
##################

# gen_sqlite_db
- Creates a Sqlite3 database exactly as specified in the PowerDNS documentation.

# zonefiles2sql (path_zone_files, db_path)
- Adds the entries of the BIND zone files to the database with the BIND method zone2sql. The BIND zone files are stored in the folder specified in the config.ini.

# domain_update (db_path, conn_db)
- Adds the matching domain ID of the newly added entries to the records table of the database

# domain_id (conn_db)
- Adds the nonexistent domain name to the domains table of the database

# reverse_ipv6 (conn_db)
- For all ipv6 entries that do not have a PTR entry, a PTR entry is created and added to the database.

# reverse_ipv4 (conn_db)
- For all ipv4 entries that do not have a PTR entry, a PTR entry is created and added to the database.

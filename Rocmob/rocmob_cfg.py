import pymysql as MySQLdb

host = 'database-1.cnzdf3aq4zqs.us-west-1.rds.amazonaws.com'
user = 'admin'
password = 'fg3ey6esbmYnvQv'
db = 'smart_db'

conn = MySQLdb.connect(host=host, user=user, passwd=password, db=db,
            port=3306, charset='utf8', use_unicode=True)

cursor = conn.cursor()

my_query="""
CREATE TABLE `rocmob` (
  `sk` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL,
  `dealership_name` mediumtext,
  `dealer_type` mediumtext,
  `dealership_address` mediumtext,
  `dealership_phone` mediumtext,
  `store_code` mediumtext,
  `dealer_url` mediumtext,
  `CMS` mediumtext,
  `Condition_` mediumtext,
  `Year_` mediumtext,
  `Make` mediumtext,
  `Model` mediumtext,
  `Brand` mediumtext,
  `VIN` mediumtext,
  `Stock_Number` mediumtext,
  `URL` mediumtext,
  `MSRP` mediumtext,
  `Price` mediumtext,
  `Savings` mediumtext,
  `Finance_option` mediumtext,
  `Special_Tag` mediumtext,
  `Type_` mediumtext,
  `Sub_Type` mediumtext,
  `Location` mediumtext,
  `Image_URL` mediumtext,
  `Image_URL_2` mediumtext,
  `Image_URL_3` mediumtext,
  `Title` mediumtext,
  `Description` mediumtext,
  `Trim` mediumtext,
  `Length` mediumtext,
  `Doors` mediumtext,
  `Drivetrain` mediumtext,
  `Fuel_Type` mediumtext,
  `exterior_color` mediumtext,
  `interior_color` mediumtext,
  `Sleeps` mediumtext,
  `seats` mediumtext,
  `Dry_Weight` mediumtext,
  `mileage_value` mediumtext,
  `mileage_unit` mediumtext,
  `engine` mediumtext,
  `Transmission` mediumtext,
  `body_style` mediumtext,
  `Features` mediumtext,
  `custom_label_0` mediumtext,
  `custom_label_1` mediumtext,
  `custom_label_2` mediumtext,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `modified_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
"""

#####cursor.execute(my_query)


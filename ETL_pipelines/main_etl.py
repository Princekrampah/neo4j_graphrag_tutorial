import os
import logging
from retry import retry
from dotenv import load_dotenv
from neo4j import GraphDatabase
import pandas as pd

# Load environment variables
load_dotenv()

# Load file paths
CATEGORY_CSV_FILEPATH = os.getenv("CATEGORY_CSV_FILE_PATH")
PRODUCT_CSV_FILE_PATH = os.getenv("PRODUCT_CSV_FILE_PATH")
SUPPLIER_CSV_FILE_PATH = os.getenv("SUPPLIER_CSV_FILE_PATH")
ORDER_CSV_FILE_PATH = os.getenv("ORDER_CSV_FILE_PATH")
ORDER_DETAILS_CSV_FILE_PATH = os.getenv("ORDER_DETAILS_CSV_FILE_PATH")
SHIPPER_CSV_FILE_PATH = os.getenv("SHIPPERS_CSV_FILE_PATH")
EMPLOYEE_CSV_FILE_PATH = os.getenv("EMPLOYEE_CSV_FILE_PATH")
CUSTOMER_CSV_FILE_PATH = os.getenv("CUSTOMER_CSV_FILE_PATH")

# Load Neo4j credentials
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")


# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

LOGGER = logging.getLogger(__name__)

NODES = [
    "Product", "Supplier",
    "Category", "Order",
    "Shipper", "Employee",
    "Customer"
]


@retry(tries=10, delay=10)
def set_uniquness_constraints(tx, node):
    query = f"""CREATE CONSTRAINT IF NOT EXISTS FOR 
    (n:{node}) REQUIRE n.id IS UNIQUE;"""

    _ = tx.run(query)


@retry(tries=10, delay=10)
def create_uniqueness_constraints():
    LOGGER.info("Connecting to Neo4j...")
    driver = GraphDatabase.driver(
        NEO4J_URI,
        auth=(NEO4J_USERNAME, NEO4J_PASSWORD)
    )

    LOGGER.info("Creating uniqueness constraints...")

    with driver.session() as session:
        for node in NODES:
            session.execute_write(set_uniquness_constraints, node)


def process_product_category_supplier_csv(
    product_file_path: str,
    category_file_path: str,
    supplier_file_path: str,
) -> pd.DataFrame:
    """
    Reads and processes CSV files containing product, category, and supplier data, merging them into a single DataFrame.

    This function reads data from three CSV files (product, category, and supplier), merges the data based on the 
    'categoryID' and 'supplierID' columns, and cleans the resulting DataFrame by replacing missing values in specific 
    columns with 'Unknown'.

    :param product_file_path: The file path to the CSV file containing product data.
    :param category_file_path: The file path to the CSV file containing category data.
    :param supplier_file_path: The file path to the CSV file containing supplier data.
    :return: A pandas DataFrame containing the merged product, category, and supplier data.
    """

    try:
        LOGGER.info(f"Reading data from {product_file_path}")
        product_df = pd.read_csv(product_file_path)

        LOGGER.info(f"Reading data from {category_file_path}")
        category_df = pd.read_csv(category_file_path)

        LOGGER.info("Merging product and category data")
        product_category_df = pd.merge(
            product_df, category_df, on='categoryID')

        LOGGER.info(f"Reading data from {supplier_file_path}")
        supplier_df = pd.read_csv(supplier_file_path)

        LOGGER.info("Merging product, category and supplier data")
        product_category_supplier_df = pd.merge(
            product_category_df, supplier_df, on='supplierID', how='left')

        LOGGER.info("Cleaning data, replacing NA values with Unknown")
        product_category_supplier_df["region"] = product_category_supplier_df["region"].replace({
                                                                                                pd.NA: "Unknown"})
        product_category_supplier_df["fax"] = product_category_supplier_df["fax"].replace({
                                                                                          pd.NA: "Unknown"})
        product_category_supplier_df["homePage"] = product_category_supplier_df["homePage"].replace({
                                                                                                    pd.NA: "Unknown"})

        return product_category_supplier_df
    except Exception as e:
        LOGGER.error(f"Error reading CSV data: {e}")


def insert_data(tx, row):
    """
    Inserts product, category, and supplier data into a Neo4j graph database.

    This function creates a product node, merges category and supplier nodes, and 
    establishes relationships between the product and its category and supplier in 
    the Neo4j graph. The data is passed as a dictionary in the `row` parameter.

    :param tx: The transaction object used to execute the Cypher queries in the Neo4j database.
    :param row: A dictionary containing the product, category, and supplier data to be inserted.
    """

    tx.run('''
            CREATE (product:Product {
                productID: $productID,
                productName: $productName,
                supplierID: $supplierID,
                categoryID: $categoryID,
                quantityPerUnit: $quantityPerUnit,
                unitPrice: $unitPrice,
                unitsInStock: $unitsInStock,
                unitsOnOrder: $unitsOnOrder,
                reorderLevel: $reorderLevel,
                discontinued: $discontinued
            })
            MERGE (category:Category {
                categoryID: $categoryID,
                categoryName: $categoryName,
                description: $description,
                picture: $picture
            })
            MERGE (supplier:Supplier {
                supplierID: $supplierID,
                companyName: $companyName,
                contactName: $contactName,
                contactTitle: $contactTitle,
                address: $address,
                city: $city,
                region: $region,
                postalCode: $postalCode,
                country: $country,
                phone: $phone,
                fax: $fax,
                homePage: $homePage
            })
            CREATE (product)-[:PART_OF]->(category)
            CREATE (product)-[:SUPPLIED_BY]->(supplier)
            ''', row)


@retry(tries=100, delay=10)
def load_product_category_supply_into_graph(
    product_category_supplier_df: pd.DataFrame,
):
    """
    Loads product, category, and supplier data into a Neo4j graph database.

    This function connects to a Neo4j database and inserts data from a pandas DataFrame 
    that contains product, category, and supplier information. The data is inserted 
    into the graph using a write transaction. The function uses retry logic to ensure 
    successful data insertion, retrying up to 100 times with a 10-second delay between attempts.

    :param product_category_supplier_df: A pandas DataFrame containing the product, category, 
                                         and supplier data to be inserted into the graph.
    """

    LOGGER.info("Connecting to Neo4j")
    driver = GraphDatabase.driver(
        NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD)
    )

    LOGGER.info("Inserting data into Neo4j")
    with driver.session() as session:
        for _, row in product_category_supplier_df.iterrows():
            session.execute_write(insert_data, row.to_dict())

    LOGGER.info("Data inserted into Neo4j")

    driver.close()


def process_order_order_details_product_shipper_employee_customer_csv(
    order_file_path: str,
    order_details_file_path: str,
    customer_file_path: str,
    shipper_file_path: str,
    employee_file_path: str,
) -> pd.DataFrame:
    """
    Processes and merges data from multiple CSV files containing order, order details, 
    customer, shipper, and employee information, and prepares it for further analysis.

    This function reads the provided CSV files, merges them into a single DataFrame, 
    and cleans the data by replacing missing values. The final DataFrame is returned 
    for use in other operations, such as inserting the data into a Neo4j database.

    :param order_file_path: The file path to the orders CSV file.
    :param order_details_file_path: The file path to the order details CSV file.
    :param customer_file_path: The file path to the customers CSV file.
    :param shipper_file_path: The file path to the shippers CSV file.
    :param employee_file_path: The file path to the employees CSV file.
    :return: A pandas DataFrame containing the merged and cleaned data.
    """

    LOGGER.info("Reading data...")

    orders_df = pd.read_csv(order_file_path)
    order_details_df = pd.read_csv(order_details_file_path)
    customer_df = pd.read_csv(customer_file_path)
    shipper_df = pd.read_csv(shipper_file_path)
    employee_df = pd.read_csv(employee_file_path)

    LOGGER.info("Merging order and order details data...")
    orders_order_details_df = pd.merge(
        orders_df,
        order_details_df,
        on='orderID',
        how='left'
    )

    LOGGER.info("Merging order and order details data with customer data...")
    orders_order_details_customer_df = pd.merge(
        orders_order_details_df,
        customer_df,
        on='customerID',
        how='left'
    )

    LOGGER.info(
        "Merging order and order details data with customer data and shipper data...")
    orders_order_details_customer_shipper_df = pd.merge(
        orders_order_details_customer_df,
        shipper_df,
        left_on='shipVia',
        right_on="shipperID",
        how='left'
    )

    LOGGER.info(
        "Merging order and order details data with customer data, shipper data and employee data...")
    orders_order_details_customer_shipper_employee_df = pd.merge(
        orders_order_details_customer_shipper_df,
        employee_df,
        left_on='employeeID',
        right_on='employeeID',
        how='left'
    )

    LOGGER.info("Cleaning data...")
    orders_order_details_customer_shipper_employee_df.replace(
        {pd.NA: "Unknown"}, inplace=True)

    # Change to integer
    orders_order_details_customer_shipper_employee_df["reportsTo"] = orders_order_details_customer_shipper_employee_df["reportsTo"].astype(
        'Int64')
    orders_order_details_customer_shipper_employee_df["reportsTo"]

    # Replace missing values
    orders_order_details_customer_shipper_employee_df["reportsTo"] = orders_order_details_customer_shipper_employee_df["reportsTo"].replace({
                                                                                                                                            pd.NA: 2})

    return orders_order_details_customer_shipper_employee_df


@retry(tries=100, delay=10)
def create_manager(tx, row):
    """
    Creates or updates an Employee node in the Neo4j database.

    This function uses the Cypher MERGE statement to ensure that an Employee node
    with the specified properties is created. If an Employee node with the given
    employeeID already exists, it will be updated with the provided properties.
    """

    tx.run("""
        MERGE (e:Employee {
            employeeID: $employeeID,
            lastName: $lastName,
            firstName: $firstName,
            title: $title,
            titleOfCourtesy: $titleOfCourtesy,
            birthDate: $birthDate,
            hireDate: $hireDate,
            address: $address_y,
            city: $city_y,
            region: $region_y,
            postalCode: $postalCode_y,
            country: $country_y,
            homePhone: $homePhone,
            extension: $extension,
            photo: $photo,
            notes: $notes,
            photoPath: $photoPath
    })
    """, row)


@retry(tries=100, delay=10)
def insert_manager_record(
    orders_order_details_customer_shipper_employee_df: pd.DataFrame
) -> None:
    """
    Inserts records of employees with the title 'Vice President' into the Neo4j database.

    This function connects to a Neo4j database and creates nodes for employees who have
    the title 'Vice President'. It filters the provided DataFrame to find these records
    and then inserts them into the database using a Neo4j transaction.

    :param orders_order_details_customer_shipper_employee_df: A pandas DataFrame containing
        employee records, including titles and other relevant information.
    """

    LOGGER.info("Connecting to Neo4j")
    driver = GraphDatabase.driver(
        NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD)
    )

    LOGGER.info("Creating vice president node...")
    vice_president = orders_order_details_customer_shipper_employee_df[
        orders_order_details_customer_shipper_employee_df["title"] == "Vice President"]

    LOGGER.info("Inserting data into Neo4j")
    with driver.session() as session:
        for _, row in vice_president.iterrows():
            session.write_transaction(create_manager, row.to_dict())

    LOGGER.info("Vice president node created")

    driver.close()


def order_order_details_shippers_employees_and_customer_data_ingester(tx, row):
    """
    Ingests order-related data into the Neo4j database, creating and merging nodes and relationships
    for orders, products, customers, shippers, and employees.

    This function handles the creation of nodes for Orders, Customers, Shippers, and Employees,
    and establishes relationships between them based on the provided data. It also links employees
    to their managers if applicable.

    :param tx: The Neo4j transaction context to execute the query.
    :param row: A dictionary containing the data for the order, product, customer, shipper, 
                and employee nodes, including relationships such as manager reporting.
    """

    tx.run("""
    CREATE (o:Order {
        orderID: $orderID,
        orderDate: $orderDate,
        requiredDate: $requiredDate,
        shippedDate: $shippedDate,
        shipVia: $shipVia,
        freight: $freight,
        shipName: $shipName,
        shipAddress: $shipAddress,
        shipCity: $shipCity,
        shipRegion: $shipRegion,
        shipPostalCode: $shipPostalCode,
        shipCountry: $shipCountry
    })
    WITH o
    MATCH (p:Product { productID: $productID })
    WITH p, o
    MERGE (c:Customer {
        customerID: $customerID,
        companyName: $companyName_x,
        contactName: $contactName,
        contactTitle: $contactTitle,
        address: $address_x,
        city: $city_x,
        region: $region_x,
        postalCode: $postalCode_x,
        country: $country_x,
        phone: $phone_x,
        fax: $fax
    })
    WITH c, p, o
    MERGE (s:Shipper {
        shipperID: $shipperID,
        companyName: $companyName_y,
        phone: $phone_y
    })
    WITH s, c, p, o
    MERGE (e:Employee {
        employeeID: $employeeID,
        lastName: $lastName,
        firstName: $firstName,
        title: $title,
        titleOfCourtesy: $titleOfCourtesy,
        birthDate: $birthDate,
        hireDate: $hireDate,
        address: $address_y,
        city: $city_y,
        region: $region_y,
        postalCode: $postalCode_y,
        country: $country_y,
        homePhone: $homePhone,
        extension: $extension,
        photo: $photo,
        notes: $notes,
        photoPath: $photoPath
    })
    WITH e, s, c, p, o
    MATCH (m:Employee { employeeID: $reportsTo }) // Assuming reportsTo is the ID of the manager
    WITH m, e, s, c, p, o
    MERGE (e)-[:REPORTS_TO]->(m)
    MERGE (o)-[:INCLUDES]->(p)
    MERGE (o)-[:ORDERED_BY]->(c)
    MERGE (o)-[:SHIPPED_BY]->(s)
    MERGE (o)-[:PROCESSED_BY]->(e)
    """, parameters=row)


@retry(tries=100, delay=10)
def load_order_order_details_shippers_employees_and_customer_data_into_graph(
    orders_order_details_customer_shipper_employee_df: pd.DataFrame,
):
    """
    Load order, order details, shippers, employees and customer data into Neo4j.
    """
    LOGGER.info("Connecting to Neo4j")
    driver = GraphDatabase.driver(
        NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD)
    )

    LOGGER.info("Inserting data into Neo4j")
    with driver.session() as session:
        for _, row in orders_order_details_customer_shipper_employee_df.iterrows():
            session.execute_write(
                order_order_details_shippers_employees_and_customer_data_ingester, row.to_dict())

    LOGGER.info("Data inserted into Neo4j")

    driver.close()


def main():
    LOGGER.info("Creating uniqueness constraints...")
    create_uniqueness_constraints()
    LOGGER.info("Uniqueness constraints created successfully.")

    LOGGER.info("Processing product, category, and supplier data...")
    product_category_supplier_df = process_product_category_supplier_csv(
        PRODUCT_CSV_FILE_PATH, CATEGORY_CSV_FILEPATH, SUPPLIER_CSV_FILE_PATH
    )
    LOGGER.info("Data processed successfully.")

    LOGGER.info("Loading product, category, and supplier data into Neo4j...")
    load_product_category_supply_into_graph(product_category_supplier_df)
    LOGGER.info("Data loaded successfully.")

    LOGGER.info(
        "Processing order, order details, customer, shipper, and employee data...")
    orders_order_details_customer_shipper_employee_df = process_order_order_details_product_shipper_employee_customer_csv(
        ORDER_CSV_FILE_PATH, ORDER_DETAILS_CSV_FILE_PATH, CUSTOMER_CSV_FILE_PATH, SHIPPER_CSV_FILE_PATH, EMPLOYEE_CSV_FILE_PATH
    )

    LOGGER.info("Inserting manager records into Neo4j...")
    insert_manager_record(orders_order_details_customer_shipper_employee_df)
    LOGGER.info("Manager records inserted successfully.")

    LOGGER.info(
        "Loading order, order details, shippers, employees, and customer data into Neo4j...")
    load_order_order_details_shippers_employees_and_customer_data_into_graph(
        orders_order_details_customer_shipper_employee_df[:250])
    LOGGER.info("Data loaded successfully.")


if __name__ == "__main__":
    main()

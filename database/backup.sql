-- MySQL dump 10.13  Distrib 8.0.43, for Win64 (x86_64)
--
-- Host: 127.0.0.1    Database: company_db
-- ------------------------------------------------------
-- Server version	9.4.0

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `edit_logs`
--

DROP TABLE IF EXISTS `edit_logs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `edit_logs` (
  `id` int NOT NULL AUTO_INCREMENT,
  `table_name` varchar(50) NOT NULL,
  `record_id` int NOT NULL,
  `field_name` varchar(50) NOT NULL,
  `old_value` text,
  `new_value` text,
  `edited_by` varchar(50) NOT NULL,
  `edit_time` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `edit_logs`
--

LOCK TABLES `edit_logs` WRITE;
/*!40000 ALTER TABLE `edit_logs` DISABLE KEYS */;
/*!40000 ALTER TABLE `edit_logs` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `employee_transactions`
--

DROP TABLE IF EXISTS `employee_transactions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `employee_transactions` (
  `id` int NOT NULL AUTO_INCREMENT,
  `employee_id` int NOT NULL,
  `transaction_date` date NOT NULL,
  `type` enum('credit','debit') NOT NULL,
  `amount` decimal(10,2) NOT NULL,
  `description` text,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `employee_id` (`employee_id`),
  CONSTRAINT `employee_transactions_ibfk_1` FOREIGN KEY (`employee_id`) REFERENCES `employees` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=18 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `employee_transactions`
--

LOCK TABLES `employee_transactions` WRITE;
/*!40000 ALTER TABLE `employee_transactions` DISABLE KEYS */;
INSERT INTO `employee_transactions` VALUES (2,10,'2025-10-09','debit',3000.00,'Update','2025-10-08 16:52:32'),(3,10,'2025-10-08','credit',500.00,'ADvance','2025-10-08 16:58:16'),(4,10,'2025-10-08','debit',700.00,'dews Paid','2025-10-08 16:58:51'),(5,10,'2025-10-09','debit',100.00,'','2025-10-08 17:40:52'),(6,10,'2025-10-09','credit',200.00,'','2025-10-08 17:41:21'),(7,10,'2025-10-09','debit',100.00,'medical','2025-10-08 18:20:42'),(8,10,'2025-10-10','debit',200.00,'medical','2025-10-08 18:33:23'),(9,10,'2025-10-10','credit',300.00,'','2025-10-08 18:39:15'),(10,9,'2025-10-09','debit',500.00,'for breakfast','2025-10-09 10:12:25'),(11,9,'2025-10-10','credit',100.00,'','2025-10-09 10:13:03'),(12,10,'2025-10-09','credit',3000.00,'','2025-10-09 16:36:49'),(13,10,'2025-10-09','debit',400.00,'','2025-10-09 16:37:13'),(14,14,'2025-10-28','debit',200.00,'Advance','2025-10-28 08:10:47'),(15,14,'2025-10-29','credit',3000.00,'incentive credit','2025-10-28 08:11:21'),(16,10,'2025-10-31','debit',100.00,'Travel Expense\r\n','2025-10-30 04:51:45'),(17,10,'2025-10-30','credit',700.00,'save','2025-10-30 04:52:30');
/*!40000 ALTER TABLE `employee_transactions` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `employees`
--

DROP TABLE IF EXISTS `employees`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `employees` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  `position` varchar(100) DEFAULT NULL,
  `email` varchar(255) DEFAULT NULL,
  `phone` varchar(255) DEFAULT NULL,
  `join_date` date DEFAULT (curdate()),
  `status` enum('active','inactive') DEFAULT 'active',
  `image` varchar(255) DEFAULT NULL,
  `document` varchar(255) DEFAULT NULL,
  `city` varchar(100) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=15 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `employees`
--

LOCK TABLES `employees` WRITE;
/*!40000 ALTER TABLE `employees` DISABLE KEYS */;
INSERT INTO `employees` VALUES (8,'Ajay kumar','Sales Executive','Ashish123@gmail.com','1234567890','2025-08-20','active','1.jpeg','flutter_uni1.pptx.pdf','Surat'),(9,'Ashish Kumar','developer','abc@gmail.com','2525252525','2025-08-20','active','1.jpeg',NULL,'Kheda'),(10,'Ajay','developer','ajay@gmail.com','1234567890','2025-08-22','active','1.jpeg','flutter_uni1.pptx.pdf','Khed'),(12,'ajay','developer','123@gmail.com','1234567890','2025-09-07','active',NULL,NULL,'nadiad'),(13,'Babubhai','Sales Executive','1234@gmail.com','7894561235','2025-09-25','active','admin-1.png',NULL,'Kheda'),(14,'Santosh Singh','Sales Executive','realhealth.rahul@gmail.com','9924440257','2025-10-28','active','IMG_4656.jpeg',NULL,'Nadiad');
/*!40000 ALTER TABLE `employees` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `evening_item`
--

DROP TABLE IF EXISTS `evening_item`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `evening_item` (
  `id` int NOT NULL AUTO_INCREMENT,
  `settle_id` int NOT NULL,
  `product_id` int NOT NULL,
  `total_qty` int NOT NULL,
  `sold_qty` int NOT NULL DEFAULT '0',
  `return_qty` int NOT NULL DEFAULT '0',
  `remaining_qty` int GENERATED ALWAYS AS (((`total_qty` - `sold_qty`) - `return_qty`)) STORED,
  `unit_price` decimal(10,2) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `settle_id` (`settle_id`),
  KEY `product_id` (`product_id`),
  CONSTRAINT `evening_item_ibfk_1` FOREIGN KEY (`settle_id`) REFERENCES `evening_settle` (`id`) ON DELETE CASCADE,
  CONSTRAINT `evening_item_ibfk_2` FOREIGN KEY (`product_id`) REFERENCES `products` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=45 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `evening_item`
--

LOCK TABLES `evening_item` WRITE;
/*!40000 ALTER TABLE `evening_item` DISABLE KEYS */;
INSERT INTO `evening_item` (`id`, `settle_id`, `product_id`, `total_qty`, `sold_qty`, `return_qty`, `unit_price`) VALUES (17,16,9,10,5,5,100.00),(29,24,13,10,5,2,100.00),(33,28,9,10,5,0,120.00),(34,28,7,5,2,0,22500.00),(35,29,14,10,10,0,100.00),(36,29,7,5,1,0,500.00),(37,30,14,10,5,0,200.00),(38,30,15,20,10,0,500.00),(39,31,9,7,5,0,120.00),(40,31,13,6,3,0,1300.00),(41,32,14,10,2,0,500.00),(42,32,13,5,3,0,1500.00),(43,32,9,10,4,0,120.00),(44,34,17,100,40,0,100.00);
/*!40000 ALTER TABLE `evening_item` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `evening_settle`
--

DROP TABLE IF EXISTS `evening_settle`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `evening_settle` (
  `id` int NOT NULL AUTO_INCREMENT,
  `allocation_id` int NOT NULL,
  `employee_id` int NOT NULL,
  `date` date NOT NULL,
  `total_amount` decimal(12,2) DEFAULT '0.00',
  `online_money` decimal(10,2) DEFAULT '0.00',
  `cash_money` decimal(10,2) DEFAULT '0.00',
  `discount` decimal(10,2) DEFAULT '0.00',
  `due_amount` decimal(12,2) GENERATED ALWAYS AS ((`total_amount` - ((`online_money` + `cash_money`) + `discount`))) STORED,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `allocation_id` (`allocation_id`),
  KEY `employee_id` (`employee_id`),
  CONSTRAINT `evening_settle_ibfk_1` FOREIGN KEY (`allocation_id`) REFERENCES `morning_allocations` (`id`),
  CONSTRAINT `evening_settle_ibfk_2` FOREIGN KEY (`employee_id`) REFERENCES `employees` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=35 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `evening_settle`
--

LOCK TABLES `evening_settle` WRITE;
/*!40000 ALTER TABLE `evening_settle` DISABLE KEYS */;
INSERT INTO `evening_settle` (`id`, `allocation_id`, `employee_id`, `date`, `total_amount`, `online_money`, `cash_money`, `discount`, `created_at`) VALUES (1,1,10,'2025-08-27',700.00,100.00,0.00,0.00,'2025-08-27 13:25:50'),(3,5,8,'2025-08-27',500.00,500.00,0.00,0.00,'2025-08-27 13:27:27'),(5,6,10,'2025-08-30',2000.00,2000.00,0.00,0.00,'2025-08-27 13:29:32'),(7,7,10,'2025-08-31',10000.00,0.00,0.00,0.00,'2025-08-27 14:04:23'),(9,8,10,'2025-08-28',1300.00,0.00,0.00,0.00,'2025-08-27 14:44:50'),(16,15,10,'2025-07-01',5500.00,0.00,0.00,0.00,'2025-08-31 05:10:46'),(18,17,8,'2025-09-15',1500.00,500.00,1000.00,0.00,'2025-08-31 05:38:30'),(20,18,10,'2025-09-25',1990.00,990.00,1000.00,0.00,'2025-08-31 05:43:04'),(21,19,10,'2025-09-14',2000.00,1500.00,500.00,0.00,'2025-08-31 05:47:06'),(22,20,8,'2025-09-20',6200.00,5100.00,1100.00,0.00,'2025-08-31 05:51:12'),(24,22,8,'2025-10-01',2500.00,1500.00,1000.00,0.00,'2025-08-31 09:01:50'),(28,12,9,'2025-09-01',45600.00,0.00,0.00,0.00,'2025-09-07 09:33:52'),(29,24,9,'2025-09-09',1500.00,500.00,800.00,200.00,'2025-09-09 15:42:23'),(30,26,10,'2025-09-10',6000.00,500000.00,250000.00,540.00,'2025-09-09 20:39:55'),(31,28,9,'2025-09-18',4500.00,250.00,530.00,3720.00,'2025-09-18 17:22:55'),(32,30,10,'2025-09-19',5980.00,5000.00,900.00,80.00,'2025-09-19 16:18:19'),(34,31,14,'2025-10-28',4000.00,1000.00,2500.00,500.00,'2025-10-28 08:09:05');
/*!40000 ALTER TABLE `evening_settle` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `expensecategories`
--

DROP TABLE IF EXISTS `expensecategories`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `expensecategories` (
  `category_id` int NOT NULL AUTO_INCREMENT,
  `category_name` varchar(100) NOT NULL,
  PRIMARY KEY (`category_id`),
  UNIQUE KEY `category_name` (`category_name`)
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `expensecategories`
--

LOCK TABLES `expensecategories` WRITE;
/*!40000 ALTER TABLE `expensecategories` DISABLE KEYS */;
INSERT INTO `expensecategories` VALUES (3,'Bills'),(5,'Food'),(6,'Light Bill'),(4,'Rent'),(8,'Travel');
/*!40000 ALTER TABLE `expensecategories` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `expenses`
--

DROP TABLE IF EXISTS `expenses`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `expenses` (
  `expense_id` int NOT NULL AUTO_INCREMENT,
  `expense_date` date NOT NULL,
  `amount` decimal(10,2) NOT NULL,
  `description` text,
  `subcategory_id` int NOT NULL,
  `payment_method` varchar(50) DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`expense_id`),
  KEY `subcategory_id` (`subcategory_id`),
  CONSTRAINT `expenses_ibfk_1` FOREIGN KEY (`subcategory_id`) REFERENCES `expensesubcategories` (`subcategory_id`)
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `expenses`
--

LOCK TABLES `expenses` WRITE;
/*!40000 ALTER TABLE `expenses` DISABLE KEYS */;
INSERT INTO `expenses` VALUES (2,'2025-09-23',8000.00,'',3,'UPI','2025-09-21 18:36:42'),(3,'2025-09-25',6000.00,'',1,'Bank Transfer','2025-09-21 18:42:54'),(4,'2025-09-23',100.00,'',4,'Cash','2025-09-21 19:05:20'),(5,'2025-09-22',300.00,'',1,'Cash','2025-09-22 16:25:38'),(6,'2025-09-23',500.00,'',5,'UPI','2025-09-23 11:06:28'),(7,'2025-09-24',10000.00,'',2,'Cash','2025-09-23 11:07:36'),(8,'2025-10-09',800.00,'',6,'Cash','2025-10-09 16:53:01');
/*!40000 ALTER TABLE `expenses` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `expensesubcategories`
--

DROP TABLE IF EXISTS `expensesubcategories`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `expensesubcategories` (
  `subcategory_id` int NOT NULL AUTO_INCREMENT,
  `subcategory_name` varchar(100) NOT NULL,
  `category_id` int NOT NULL,
  PRIMARY KEY (`subcategory_id`),
  KEY `category_id` (`category_id`),
  CONSTRAINT `expensesubcategories_ibfk_1` FOREIGN KEY (`category_id`) REFERENCES `expensecategories` (`category_id`)
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `expensesubcategories`
--

LOCK TABLES `expensesubcategories` WRITE;
/*!40000 ALTER TABLE `expensesubcategories` DISABLE KEYS */;
INSERT INTO `expensesubcategories` VALUES (1,'light Bills',3),(2,'Wi-Fi bill',3),(3,'office',4),(4,'Breakfast',5),(5,'ice-cream',5),(6,'Monthly travel pass',8);
/*!40000 ALTER TABLE `expensesubcategories` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `morning_allocation_items`
--

DROP TABLE IF EXISTS `morning_allocation_items`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `morning_allocation_items` (
  `id` int NOT NULL AUTO_INCREMENT,
  `allocation_id` int NOT NULL,
  `product_id` int NOT NULL,
  `opening_qty` int NOT NULL DEFAULT '0',
  `given_qty` int NOT NULL DEFAULT '0',
  `unit_price` decimal(10,2) NOT NULL DEFAULT '0.00',
  `total_qty` int GENERATED ALWAYS AS ((`opening_qty` + `given_qty`)) STORED,
  `amount` decimal(12,2) GENERATED ALWAYS AS ((`total_qty` * `unit_price`)) STORED,
  PRIMARY KEY (`id`),
  KEY `allocation_id` (`allocation_id`),
  KEY `product_id` (`product_id`),
  CONSTRAINT `morning_allocation_items_ibfk_1` FOREIGN KEY (`allocation_id`) REFERENCES `morning_allocations` (`id`) ON DELETE CASCADE,
  CONSTRAINT `morning_allocation_items_ibfk_2` FOREIGN KEY (`product_id`) REFERENCES `products` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=54 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `morning_allocation_items`
--

LOCK TABLES `morning_allocation_items` WRITE;
/*!40000 ALTER TABLE `morning_allocation_items` DISABLE KEYS */;
INSERT INTO `morning_allocation_items` (`id`, `allocation_id`, `product_id`, `opening_qty`, `given_qty`, `unit_price`) VALUES (1,1,9,0,8,100.00),(2,1,7,0,2,200.00),(3,2,9,0,10,100.00),(4,2,7,0,5,200.00),(5,3,9,0,20,100.00),(6,4,7,0,20,100.00),(7,5,9,0,10,100.00),(8,6,9,0,50,100.00),(9,7,9,0,200,100.00),(10,8,7,1,5,200.00),(11,8,9,3,4,100.00),(12,9,9,0,10,0.00),(13,10,7,0,10,0.00),(14,11,9,0,10,0.00),(15,12,9,0,10,120.00),(16,12,7,0,5,22500.00),(17,13,7,3,5,22500.00),(18,13,9,2,5,120.00),(19,14,9,0,10,120.00),(20,14,13,0,10,1300.00),(21,14,7,0,1,30000.00),(22,15,9,0,10,100.00),(23,15,14,0,20,500.00),(24,16,14,10,5,500.00),(25,17,9,0,10,100.00),(26,17,14,0,20,100.00),(27,18,13,0,10,200.00),(28,18,14,0,20,99.00),(29,19,9,0,20,100.00),(30,19,14,0,10,200.00),(31,20,13,0,10,100.00),(32,20,7,0,5,2000.00),(33,21,9,0,10,100.00),(34,21,7,0,20,200.00),(35,22,13,0,10,100.00),(36,22,14,0,12,200.00),(37,23,9,0,10,200.00),(38,23,15,0,20,100.00),(39,24,14,0,10,100.00),(40,24,7,0,5,500.00),(41,25,13,0,10,0.00),(42,25,14,0,20,0.00),(43,26,14,0,10,200.00),(44,26,15,0,20,500.00),(45,27,14,0,200,200.00),(46,27,15,0,100,20.00),(47,28,9,0,7,120.00),(48,28,13,0,6,1300.00),(49,29,16,0,20,0.00),(50,30,14,0,10,500.00),(51,30,13,0,5,1500.00),(52,30,9,0,10,120.00),(53,31,17,0,100,100.00);
/*!40000 ALTER TABLE `morning_allocation_items` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `morning_allocations`
--

DROP TABLE IF EXISTS `morning_allocations`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `morning_allocations` (
  `id` int NOT NULL AUTO_INCREMENT,
  `employee_id` int NOT NULL,
  `date` date NOT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_employee_date` (`employee_id`,`date`),
  CONSTRAINT `morning_allocations_ibfk_1` FOREIGN KEY (`employee_id`) REFERENCES `employees` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=32 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `morning_allocations`
--

LOCK TABLES `morning_allocations` WRITE;
/*!40000 ALTER TABLE `morning_allocations` DISABLE KEYS */;
INSERT INTO `morning_allocations` VALUES (1,10,'2025-08-27','2025-08-27 11:34:22'),(2,9,'2025-08-27','2025-08-27 12:01:56'),(3,8,'2025-08-28','2025-08-27 12:38:54'),(4,10,'2025-08-26','2025-08-27 12:50:40'),(5,8,'2025-08-27','2025-08-27 13:19:45'),(6,10,'2025-08-30','2025-08-27 13:29:05'),(7,10,'2025-08-31','2025-08-27 14:03:37'),(8,10,'2025-08-28','2025-08-27 14:43:23'),(9,9,'2025-08-28','2025-08-27 14:45:28'),(10,9,'2025-08-30','2025-08-27 14:47:42'),(11,8,'2025-08-10','2025-08-27 14:59:09'),(12,9,'2025-09-01','2025-08-27 16:09:56'),(13,9,'2025-09-02','2025-08-27 16:13:26'),(14,9,'2025-09-10','2025-08-27 16:38:24'),(15,10,'2025-07-01','2025-08-31 05:10:03'),(16,10,'2025-07-02','2025-08-31 05:11:09'),(17,8,'2025-09-15','2025-08-31 05:37:43'),(18,10,'2025-09-25','2025-08-31 05:42:31'),(19,10,'2025-09-14','2025-08-31 05:46:34'),(20,8,'2025-09-20','2025-08-31 05:50:30'),(21,9,'2025-09-26','2025-08-31 07:00:06'),(22,8,'2025-10-01','2025-08-31 09:01:13'),(23,9,'2025-08-01','2025-08-31 13:26:48'),(24,9,'2025-09-09','2025-09-09 15:41:34'),(25,8,'2025-09-10','2025-09-09 20:37:24'),(26,10,'2025-09-10','2025-09-09 20:38:19'),(27,8,'2025-09-18','2025-09-18 17:17:35'),(28,9,'2025-09-18','2025-09-18 17:20:22'),(29,8,'2025-09-19','2025-09-18 19:02:52'),(30,10,'2025-09-19','2025-09-18 20:25:12'),(31,14,'2025-10-28','2025-10-28 08:08:22');
/*!40000 ALTER TABLE `morning_allocations` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `product_returns`
--

DROP TABLE IF EXISTS `product_returns`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `product_returns` (
  `id` int NOT NULL AUTO_INCREMENT,
  `employee_id` int NOT NULL,
  `product_id` int NOT NULL,
  `quantity` int NOT NULL,
  `payment_method` enum('Cash','Online') DEFAULT 'Cash',
  `discount` decimal(10,2) DEFAULT '0.00',
  `reason` text,
  `return_date` date DEFAULT (curdate()),
  PRIMARY KEY (`id`),
  KEY `employee_id` (`employee_id`),
  KEY `product_id` (`product_id`),
  CONSTRAINT `product_returns_ibfk_1` FOREIGN KEY (`employee_id`) REFERENCES `employees` (`id`) ON DELETE CASCADE,
  CONSTRAINT `product_returns_ibfk_2` FOREIGN KEY (`product_id`) REFERENCES `products` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `product_returns`
--

LOCK TABLES `product_returns` WRITE;
/*!40000 ALTER TABLE `product_returns` DISABLE KEYS */;
/*!40000 ALTER TABLE `product_returns` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `products`
--

DROP TABLE IF EXISTS `products`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `products` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  `category` varchar(50) DEFAULT NULL,
  `stock` int NOT NULL,
  `price` decimal(10,2) DEFAULT '0.00',
  `purchase_price` decimal(10,2) NOT NULL DEFAULT '0.00' COMMENT 'Price at which the product is bought',
  `image` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=18 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `products`
--

LOCK TABLES `products` WRITE;
/*!40000 ALTER TABLE `products` DISABLE KEYS */;
INSERT INTO `products` VALUES (7,'Treadmill','None',188,2500.00,3000.00,'1.jpeg'),(9,'Footware','healthcare',1575,120.00,150.00,'magic_1.jpg'),(13,'Magic Massager','healthcare',242,1500.00,1500.00,'magic_1.jpg'),(14,'mobile','Electric',189,500.00,700.00,NULL),(15,'Mobile Cover','Electric',292,100.00,120.00,NULL),(16,'pen','stationary',116,10.00,5.00,NULL),(17,'Eye Mask','healthcare',100,100.00,100.00,NULL);
/*!40000 ALTER TABLE `products` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `purchase_items`
--

DROP TABLE IF EXISTS `purchase_items`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `purchase_items` (
  `id` int NOT NULL AUTO_INCREMENT,
  `purchase_id` int NOT NULL,
  `product_id` int NOT NULL,
  `quantity` int NOT NULL,
  `purchase_price` decimal(10,2) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `purchase_id` (`purchase_id`),
  KEY `product_id` (`product_id`),
  CONSTRAINT `purchase_items_ibfk_1` FOREIGN KEY (`purchase_id`) REFERENCES `purchases` (`id`) ON DELETE CASCADE,
  CONSTRAINT `purchase_items_ibfk_2` FOREIGN KEY (`product_id`) REFERENCES `products` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=17 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `purchase_items`
--

LOCK TABLES `purchase_items` WRITE;
/*!40000 ALTER TABLE `purchase_items` DISABLE KEYS */;
INSERT INTO `purchase_items` VALUES (1,1,15,10,100.00),(2,1,13,50,1500.00),(3,2,9,100,150.00),(4,4,13,12,1500.00),(5,4,15,102,120.00),(6,5,15,100,120.00),(7,6,7,11,3000.00),(8,7,14,10,700.00),(9,8,16,16,5.00),(10,11,9,10,150.00),(11,12,13,1,1500.00),(12,13,9,1,150.00),(13,14,9,1000,150.00),(14,14,14,10,700.00),(15,15,13,100,1500.00),(16,16,17,40,100.00);
/*!40000 ALTER TABLE `purchase_items` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `purchases`
--

DROP TABLE IF EXISTS `purchases`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `purchases` (
  `id` int NOT NULL AUTO_INCREMENT,
  `supplier_id` int NOT NULL,
  `purchase_date` date NOT NULL,
  `bill_number` varchar(50) DEFAULT NULL,
  `total_amount` decimal(12,2) NOT NULL,
  `notes` text,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `supplier_id` (`supplier_id`),
  CONSTRAINT `purchases_ibfk_1` FOREIGN KEY (`supplier_id`) REFERENCES `suppliers` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=17 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `purchases`
--

LOCK TABLES `purchases` WRITE;
/*!40000 ALTER TABLE `purchases` DISABLE KEYS */;
INSERT INTO `purchases` VALUES (1,1,'2025-09-09','',76000.00,NULL,'2025-09-09 09:27:52'),(2,1,'2025-09-09','',15000.00,NULL,'2025-09-09 09:58:00'),(4,1,'2025-09-09','',30240.00,NULL,'2025-09-09 10:56:39'),(5,1,'2025-09-09','',12000.00,NULL,'2025-09-09 15:35:25'),(6,1,'2025-09-09','',33000.00,NULL,'2025-09-09 15:36:20'),(7,1,'2025-09-09','',7000.00,NULL,'2025-09-09 15:38:15'),(8,1,'2025-09-18','',80.00,NULL,'2025-09-18 16:12:22'),(11,1,'2025-10-09','',1500.00,NULL,'2025-10-09 16:41:07'),(12,1,'2025-10-09','',1500.00,NULL,'2025-10-09 16:42:02'),(13,1,'2025-10-09','',150.00,NULL,'2025-10-09 16:43:01'),(14,2,'2025-10-28','',157000.00,NULL,'2025-10-28 08:02:02'),(15,1,'2025-10-28','',150000.00,NULL,'2025-10-28 08:05:09'),(16,2,'2025-10-28','',4000.00,NULL,'2025-10-28 08:13:20');
/*!40000 ALTER TABLE `purchases` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `sales`
--

DROP TABLE IF EXISTS `sales`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sales` (
  `id` int NOT NULL AUTO_INCREMENT,
  `product_id` int NOT NULL,
  `quantity` int NOT NULL,
  `price` decimal(10,2) NOT NULL,
  `discount` decimal(10,2) DEFAULT '0.00',
  `payment_mode` enum('cash','online') NOT NULL,
  `payment_remark` enum('credit','debit') DEFAULT 'debit',
  `sale_date` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `product_id` (`product_id`),
  CONSTRAINT `sales_ibfk_1` FOREIGN KEY (`product_id`) REFERENCES `products` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `sales`
--

LOCK TABLES `sales` WRITE;
/*!40000 ALTER TABLE `sales` DISABLE KEYS */;
/*!40000 ALTER TABLE `sales` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `supplier_payments`
--

DROP TABLE IF EXISTS `supplier_payments`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `supplier_payments` (
  `id` int NOT NULL AUTO_INCREMENT,
  `supplier_id` int NOT NULL,
  `payment_date` date NOT NULL,
  `amount_paid` decimal(12,2) NOT NULL,
  `payment_mode` varchar(50) DEFAULT 'Cash',
  `notes` text,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `supplier_id` (`supplier_id`),
  CONSTRAINT `supplier_payments_ibfk_1` FOREIGN KEY (`supplier_id`) REFERENCES `suppliers` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=10 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `supplier_payments`
--

LOCK TABLES `supplier_payments` WRITE;
/*!40000 ALTER TABLE `supplier_payments` DISABLE KEYS */;
INSERT INTO `supplier_payments` VALUES (1,1,'2025-09-09',2000.00,'UPI','','2025-09-09 09:51:35'),(2,1,'2025-09-09',4000.00,'Bank Transfer','','2025-09-09 09:53:46'),(3,1,'2025-09-18',80.00,'Cheque','','2025-09-18 16:12:53'),(4,1,'2025-09-19',10000.00,'Bank Transfer','','2025-09-19 16:23:21'),(5,1,'2025-10-09',158000.00,'Cash','','2025-10-09 16:40:14'),(6,1,'2025-10-09',800.00,'Cash','','2025-10-09 16:41:35'),(7,1,'2025-10-09',800.00,'Cash','','2025-10-09 16:41:35'),(8,1,'2025-10-09',700.00,'Cash','','2025-10-09 16:42:40'),(9,1,'2025-10-28',150000.00,'Bank Transfer','test','2025-10-28 08:03:52');
/*!40000 ALTER TABLE `supplier_payments` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `suppliers`
--

DROP TABLE IF EXISTS `suppliers`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `suppliers` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  `phone` varchar(20) DEFAULT NULL,
  `address` text,
  `gstin` varchar(15) DEFAULT NULL,
  `is_active` tinyint(1) NOT NULL DEFAULT '1',
  `current_due` decimal(12,2) NOT NULL DEFAULT '0.00',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `suppliers`
--

LOCK TABLES `suppliers` WRITE;
/*!40000 ALTER TABLE `suppliers` DISABLE KEYS */;
INSERT INTO `suppliers` VALUES (1,'REAL PROMOTION 1','09924440257','G-11 TULSIMANGLAM COMPLEX , B/H- TRIMURTI COMPLEX GHODIYA BAZAAR , STATION ROAD ( NADIAD)','',1,90.00),(2,'REAL PROMOTION','','Nadiad','',1,161000.00);
/*!40000 ALTER TABLE `suppliers` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `users`
--

DROP TABLE IF EXISTS `users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `users` (
  `id` int NOT NULL AUTO_INCREMENT,
  `username` varchar(50) NOT NULL,
  `password` varchar(255) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `users`
--

LOCK TABLES `users` WRITE;
/*!40000 ALTER TABLE `users` DISABLE KEYS */;
INSERT INTO `users` VALUES (1,'root','rahul@real');
/*!40000 ALTER TABLE `users` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-10-31 23:36:58

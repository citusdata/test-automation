import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.Random;

public class JDBCReleaseTest {

	private static final String user_name = "USER_NAME";
	static String url = "jdbc:postgresql://localhost:9700/postgres";


	public static void main(String[] args) throws SQLException {

		for (int i=0; i < 1; ++i)
		{
			test_no_1();
			test_no_2();
			test_no_3();
			test_no_4();
			test_no_6();
			test_no_7();

			simplePreparedTest1();
			simplePreparedTest2();
			simplePreparedTest3();
			simplePreparedTest4();
		}

	}


	static void test_no_1() throws SQLException
	{
		String query = "SELECT count(*) FROM orders;";
		String large_table_shard_count = "2";
		String task_executor_type = "task-tracker";

		executePreparedQuery(query, large_table_shard_count, task_executor_type);

		task_executor_type = "real-time";
		executePreparedQuery(query, large_table_shard_count, task_executor_type);
	}


	static void test_no_2() throws SQLException
	{
		String query = "SELECT count(*) FROM orders, lineitem WHERE	o_orderkey = l_orderkey;";
		String large_table_shard_count = "2";
		String task_executor_type = "task-tracker";

		executePreparedQuery(query, large_table_shard_count, task_executor_type);

		task_executor_type = "real-time";
		executePreparedQuery(query, large_table_shard_count, task_executor_type);
	}


	static void test_no_3() throws SQLException
	{
		String query = "SELECT count(*) FROM orders, customer WHERE o_custkey = c_custkey;";
		String large_table_shard_count = "2";
		String task_executor_type = "task-tracker";

		executePreparedQuery(query, large_table_shard_count, task_executor_type);
	}


	static void test_no_4() throws SQLException
	{
		String query = "SELECT count(*) FROM orders, customer, lineitem WHERE o_custkey = c_custkey AND o_orderkey = l_orderkey;";
		String large_table_shard_count = "2";
		String task_executor_type = "task-tracker";

		executePreparedQuery(query, large_table_shard_count, task_executor_type);
	}


	static void test_no_6() throws SQLException
	{
		String query = "SELECT	count(*) FROM orders, lineitem WHERE o_orderkey = l_orderkey AND l_suppkey > ?;";
		String large_table_shard_count = "2";
		String task_executor_type = "task-tracker";

		executePreparedQueryWithParam(query, large_table_shard_count, task_executor_type, 155);
		executePreparedQueryWithParam(query, large_table_shard_count, task_executor_type, 1555);

	}


	static void test_no_7() throws SQLException
	{
		String query = "SELECT supp_nation::text, cust_nation::text, l_year::int, sum(volume)::double precision AS revenue FROM ( SELECT supp_nation, cust_nation, extract(year FROM l_shipdate) AS l_year, l_extendedprice * (1 - l_discount) AS volume FROM supplier, lineitem, orders, customer, ( SELECT n1.n_nationkey AS supp_nation_key, n2.n_nationkey AS cust_nation_key, n1.n_name AS supp_nation, n2.n_name AS cust_nation FROM nation n1, nation n2 WHERE ( (n1.n_name = ? AND n2.n_name = ?) OR (n1.n_name = ? AND n2.n_name = ?) ) ) AS temp WHERE s_suppkey = l_suppkey AND o_orderkey = l_orderkey AND c_custkey = o_custkey AND s_nationkey = supp_nation_key AND c_nationkey = cust_nation_key AND l_shipdate between date '1995-01-01' AND date '1996-12-31' ) AS shipping GROUP BY supp_nation, cust_nation, l_year ORDER BY supp_nation, cust_nation, l_year; ";

		String large_table_shard_count = "2";
		String task_executor_type = "task-tracker";

		executePreparedQueryWithTwoParam(query, large_table_shard_count, task_executor_type, "RUSSIA", "UNITED STATES");
		executePreparedQueryWithTwoParam(query, large_table_shard_count, task_executor_type, "GERMANY", "FRANCE");
	}


	static void executePreparedQuery(String query, String large_table_shard_count, String task_executor_type) throws SQLException
	{

		Connection db = DriverManager.getConnection(url, user_name, "");
		Statement stmtUpdate = db.createStatement();
		stmtUpdate.executeUpdate("SET citus.large_table_shard_count TO " + large_table_shard_count );
		stmtUpdate.executeUpdate("SET citus.task_executor_type TO '" + task_executor_type + "'" );
		PreparedStatement stmt = db.prepareStatement(query);

		ResultSet rs = stmt.executeQuery();
		System.out.println("Results:");

		while (rs.next())
		{
			System.out.println("Count(*):" + rs.getString("count"));
		}
		stmtUpdate.close();
		stmt.close();
		db.close();

	}


	static void executePreparedQueryWithParam(String query, String large_table_shard_count, String task_executor_type, int param) throws SQLException
	{
		Connection db = DriverManager.getConnection(url, user_name, "");
		Statement stmtUpdate = db.createStatement();
		stmtUpdate.executeUpdate("SET citus.large_table_shard_count TO " + large_table_shard_count );
		stmtUpdate.executeUpdate("SET citus.task_executor_type TO '" + task_executor_type + "'" );
		PreparedStatement stmt = db.prepareStatement(query);
		stmt.setInt(1, param);

		ResultSet rs = stmt.executeQuery();
		System.out.println("Results:");

		while (rs.next())
		{
			System.out.println("Count(*):" + rs.getString("count"));
		}
		stmt.close();
		db.close();

	}


	static void executePreparedQueryWithTwoParam(String query, String large_table_shard_count, String task_executor_type, String param1, String param2) throws SQLException
	{
		Connection db = DriverManager.getConnection(url, user_name, "");
		Statement stmtUpdate = db.createStatement();
		stmtUpdate.executeUpdate("SET citus.large_table_shard_count TO " + large_table_shard_count );
		stmtUpdate.executeUpdate("SET citus.task_executor_type TO '" + task_executor_type + "'" );
		PreparedStatement stmt = db.prepareStatement(query);
		stmt.setString(1, param1);
		stmt.setString(2, param2);
		stmt.setString(3, param1);
		stmt.setString(4, param2);

		ResultSet rs = stmt.executeQuery();
		System.out.println("Results:");

		while (rs.next())
		{
			System.out.println("supp_nation" + rs.getString(1));
			System.out.println("cust_nation" + rs.getString(2));
			System.out.println("l_year" + rs.getInt(3));
			System.out.println("revenue" + rs.getDouble(4));
		}
		stmt.close();
		db.close();

	}


	static void executeUpdateQuery(String query) throws SQLException
	{
		Connection db = DriverManager.getConnection(url, user_name, "");
		Statement stmt = db.createStatement();
		stmt.executeUpdate(query);
		stmt.close();
		db.close();
	}


	static void simplePreparedTest1() throws SQLException
	{
		Connection db = DriverManager.getConnection(url, user_name, "");
		Statement stmt = db.createStatement();
		stmt.executeUpdate("SET citus.large_table_shard_count TO 2;");
		stmt.executeUpdate("SET citus.task_executor_type TO 'task-tracker';");
		stmt.close();
		PreparedStatement st = db.prepareStatement("SELECT count(*) FROM orders, customer WHERE o_custkey = c_custkey AND o_custkey > ?;");

		for (int i = 0; i < 10; ++i)
		{
			st.setInt(1, i);
			ResultSet rs = st.executeQuery();

			System.out.println("Results:");

			while (rs.next())
			{
			   System.out.print(rs.getString(1) + ",");
			}
			rs.close();
			 System.out.println("\nQuery returned");

		}
		st.close();
		db.close();
	}


	static void simplePreparedTest2() throws SQLException
	{
		Connection db = DriverManager.getConnection(url, user_name, "");
		Statement stmt = db.createStatement();
		stmt.executeUpdate("SET citus.large_table_shard_count TO 2;");
		PreparedStatement st = db.prepareStatement("SELECT 	l_returnflag, 	l_linestatus, 	sum(l_quantity) as sum_qty, 	sum(l_extendedprice) as sum_base_price, 	sum(l_extendedprice * (1 - l_discount)) as sum_disc_price, 	sum(l_extendedprice * (1 - l_discount) * (1 + l_tax)) as sum_charge, 	avg(l_quantity) as avg_qty, 	avg(l_extendedprice) as avg_price, 	avg(l_discount) as avg_disc, 	count(*) as count_order  FROM lineitem WHERE l_shipdate <= date '1998-12-01' - interval '90 days' GROUP BY l_returnflag,	l_linestatus ORDER BY 	l_returnflag, l_linestatus;");

		for (int i = 0; i < 10; ++i)
		{
			//st.setInt(1, i);
			ResultSet rs = st.executeQuery();
			System.out.println("Results:");

			while (rs.next())
			{
			   System.out.print(rs.getString(1) + ",");
			}
			 System.out.println("\nQuery returned");

			rs.close();

		}
		stmt.close();
		st.close();
		db.close();
	}


	static void simplePreparedTest3() throws SQLException
	{
		Connection db = DriverManager.getConnection(url, user_name, "");
		Statement stmt = db.createStatement();
		stmt.executeUpdate("SET citus.large_table_shard_count TO 2;");
		stmt.executeUpdate("SET citus.task_executor_type TO 'task-tracker';");
		PreparedStatement st = db.prepareStatement("SELECT 	l_partkey, o_orderkey, count(*)  FROM 	lineitem, orders WHERE 	l_suppkey = o_shippriority AND         l_quantity < ? AND o_totalprice <> ? GROUP BY 	l_partkey, o_orderkey ORDER BY 	l_partkey, o_orderkey;");

		for (int i = 0; i < 10; ++i)
		{
			st.setDouble(1, i);
			st.setDouble(2, i);
			System.out.println("Results:");

			ResultSet rs = st.executeQuery();
			while (rs.next())
			{
				   System.out.print(rs.getString(1) + ",");
			}

			System.out.println("Query Returned");
			rs.close();

		}
		stmt.close();
		st.close();
		db.close();
	}


	static void simplePreparedTest4() throws SQLException
	{
		Connection db = DriverManager.getConnection(url, user_name, "");
		Statement stmt = db.createStatement();
		stmt.executeUpdate("SET citus.large_table_shard_count TO 3;");
		stmt.executeUpdate("SET citus.task_executor_type TO 'task-tracker';");
		PreparedStatement st = db.prepareStatement("SELECT 	l_partkey, o_orderkey, count(*) FROM 	 lineitem, part, orders, customer WHERE l_orderkey = o_orderkey AND l_partkey = p_partkey AND 	c_custkey = o_custkey AND  (l_quantity > ? OR l_extendedprice > ?) AND p_size > 8 AND o_totalprice > ? AND  c_acctbal < ? GROUP BY 	l_partkey, o_orderkey ORDER BY l_partkey, o_orderkey LIMIT 3000;");
	    Random randomGenerator = new Random();

		for (int i = 0; i < 10; ++i)
		{
			st.setDouble(1, randomGenerator.nextInt(10));
			st.setDouble(2, randomGenerator.nextInt(10));
			st.setInt(3, randomGenerator.nextInt(10000));
			st.setDouble(4, randomGenerator.nextInt(10000));

			ResultSet rs = st.executeQuery();
			int columnCount = 0;
			while (rs.next())
			{
				++columnCount;
			}

			System.out.println("Row Count returned " + columnCount);

			rs.close();
		}
		stmt.close();
		st.close();
		db.close();
	}

}

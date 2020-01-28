import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.Random;

public class JDBCReleaseTest {

	static String url = "jdbc:postgresql://localhost:9700/postgres";


	public static void main(String[] args) throws SQLException
	{
		try {
			Class.forName("org.postgresql.Driver");
		} catch (Exception e) {
			System.out.println(e);
		}

		prep_test(args[0]);
		test_no_1(args[0]);
		test_no_2(args[0]);
		test_no_3(args[0]);
		test_no_4(args[0]);
		test_no_6(args[0]);
		//test_no_7(args[0]);
		test_no_1(args[0]);
		test_no_2(args[0]);
		test_no_3(args[0]);
		test_no_4(args[0]);
		test_no_6(args[0]);
		//test_no_7(args[0]);
		simplePreparedTest1(args[0]);
		simplePreparedTest2(args[0], args[1]);
		simplePreparedTest3(args[0]);
		simplePreparedTest4(args[0]);
	}

	static void prep_test(String task_executor_type) throws SQLException
	{
		String query = "SELECT count(*) FROM orders;";
		String large_table_shard_count = "2";

		executePreparedQuery(query, large_table_shard_count, task_executor_type);


		task_executor_type = "real-time";
	}

	static void test_no_1(String task_executor_type) throws SQLException
	{
		String query = "SELECT count(*) FROM orders;";
		String large_table_shard_count = "2";

		executePreparedQuery(query, large_table_shard_count, task_executor_type);


		task_executor_type = "real-time";
		executePreparedQuery(query, large_table_shard_count, task_executor_type);
	}

	static void test_no_2(String task_executor_type) throws SQLException
	{
		String query = "SELECT count(*) FROM orders, lineitem WHERE	o_orderkey = l_orderkey;";
		String large_table_shard_count = "2";

		executePreparedQuery(query, large_table_shard_count, task_executor_type);


		task_executor_type = "real-time";
		executePreparedQuery(query, large_table_shard_count, task_executor_type);
	}


	static void test_no_3(String task_executor_type) throws SQLException
	{
		String query = "SELECT count(*) FROM orders, customer WHERE o_custkey = c_custkey;";
		String large_table_shard_count = "2";

		executePreparedQuery(query, large_table_shard_count, task_executor_type);
	}

	static void test_no_4(String task_executor_type) throws SQLException
	{
		String query = "SELECT count(*) FROM orders, customer, lineitem WHERE o_custkey = c_custkey AND o_orderkey = l_orderkey;";
		String large_table_shard_count = "2";

		executePreparedQuery(query, large_table_shard_count, task_executor_type);
	}



	static void test_no_6(String task_executor_type) throws SQLException
	{
		String query = "SELECT	count(*) FROM orders, lineitem WHERE o_orderkey = l_orderkey AND l_suppkey > ?;";
		String large_table_shard_count = "2";

		executePreparedQueryWithParam(query, large_table_shard_count, task_executor_type, 155);

		executePreparedQueryWithParam(query, large_table_shard_count, task_executor_type, 1555);

	}

	static void test_no_7(String task_executor_type) throws SQLException
	{
		String query = "SELECT supp_nation::text, cust_nation::text, l_year::int, sum(volume)::double precision AS revenue FROM ( SELECT supp_nation, cust_nation, extract(year FROM l_shipdate) AS l_year, l_extendedprice * (1 - l_discount) AS volume FROM supplier, lineitem, orders, customer, ( SELECT n1.n_nationkey AS supp_nation_key, n2.n_nationkey AS cust_nation_key, n1.n_name AS supp_nation, n2.n_name AS cust_nation FROM nation n1, nation n2 WHERE ( (n1.n_name = ? AND n2.n_name = ?) OR (n1.n_name = ? AND n2.n_name = ?) ) ) AS temp WHERE s_suppkey = l_suppkey AND o_orderkey = l_orderkey AND c_custkey = o_custkey AND s_nationkey = supp_nation_key AND c_nationkey = cust_nation_key AND l_shipdate between date '1995-01-01' AND date '1996-12-31' ) AS shipping GROUP BY supp_nation, cust_nation, l_year ORDER BY supp_nation, cust_nation, l_year; ";

		String large_table_shard_count = "2";

		executePreparedQueryWithTwoParam(query, large_table_shard_count, task_executor_type, "RUSSIA", "UNITED STATES");
		executePreparedQueryWithTwoParam(query, large_table_shard_count, task_executor_type, "GERMANY", "FRANCE");

		System.out.println("For real now");

		large_table_shard_count = "20";
		task_executor_type = "real-time";

		executePreparedQueryWithTwoParam(query, large_table_shard_count, task_executor_type, "RUSSIA", "UNITED STATES");
		executePreparedQueryWithTwoParam(query, large_table_shard_count, task_executor_type, "GERMANY", "FRANCE");
	}


	static void executePreparedQuery(String query, String large_table_shard_count, String task_executor_type) throws SQLException
	{

		Connection db = DriverManager.getConnection(url, "pdube", "");



		Statement stmtUpdate = db.createStatement();
		stmtUpdate.executeUpdate("SET citus.enable_repartition_joins TO true;");
		stmtUpdate.executeUpdate("SET citus.large_table_shard_count TO " + large_table_shard_count );
		stmtUpdate.executeUpdate("SET citus.task_executor_type TO '" + task_executor_type + "'" );


		PreparedStatement stmt = db.prepareStatement(query);
		ResultSet rs = stmt.executeQuery();
		System.out.println("Results:");

		while (rs.next())
		{
			System.out.println("Count(*):" + rs.getString("count"));
		}
		db.close();

	}



	static void executePreparedQueryWithParam(String query, String large_table_shard_count, String task_executor_type, int param) throws SQLException
	{

		Connection db = DriverManager.getConnection(url, "pdube", "");



		Statement stmtUpdate = db.createStatement();
		stmtUpdate.executeUpdate("SET citus.enable_repartition_joins TO true;");
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
		db.close();

	}



	static void executePreparedQueryWithTwoParam(String query, String large_table_shard_count, String task_executor_type, String param1, String param2) throws SQLException
	{

		Connection db = DriverManager.getConnection(url, "pdube", "");



		Statement stmtUpdate = db.createStatement();
		stmtUpdate.executeUpdate("SET citus.enable_repartition_joins TO true");
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
		db.close();

	}



	static void executeUpdateQuery(String query) throws SQLException
	{

		Connection db = DriverManager.getConnection(url, "pdube", "");

		Statement stmt = db.createStatement();
		stmt.executeUpdate(query);

		db.close();

	}


	static void simplePreparedTest1(String task_executor_type) throws SQLException
	{
		Connection db = DriverManager.getConnection(url, "pdube", "");
		Statement stmt = db.createStatement();
		stmt.executeUpdate("SET citus.enable_repartition_joins TO true;");
		stmt.executeUpdate("SET citus.large_table_shard_count TO 2;");
		stmt.executeUpdate("SET citus.task_executor_type TO '" + task_executor_type + "'" );

		PreparedStatement st = db.prepareStatement("delete from orders where o_orderkey::text like '%88'");

		for (int i = 0; i < 1; ++i)
		{
			System.out.println(st.executeUpdate());

		}

		st = db.prepareStatement("update orders set o_totalprice = o_totalprice + 2 where o_orderkey::text like '%89'");
		for (int i = 0; i < 1; ++i)
		{
			System.out.println(st.executeUpdate());

		}
		st.close();
		st.close();
		db.close();
	}


	static void simplePreparedTest2(String task_executor_type, String distribution_type) throws SQLException
	{
		Connection db = DriverManager.getConnection(url, "pdube", "");
		Statement stmt = db.createStatement();
		stmt.executeUpdate("SET citus.enable_repartition_joins TO true;");
		stmt.executeUpdate("SET citus.large_table_shard_count TO 2;");
		stmt.executeUpdate("SET citus.task_executor_type TO '" + task_executor_type + "'" );

		if (distribution_type.equals("append"))
		{
			stmt.executeUpdate("copy orders from program 'echo 1, 1,''a'', 1.0, ''2019-01-01'', ''a'', ''a'', 1, ''a''' with csv");
		}
		PreparedStatement st = db.prepareStatement("insert into orders values (1, 1, 'a', 1.0, '2019-01-01', 'a', 'a', 1, 'a')");
		PreparedStatement st2 = db.prepareStatement("SELECT sum(o_totalprice) from orders where o_orderkey::text like '%88'");

		for (int i = 0; i < 3; ++i)
		{
			System.out.println(st.executeUpdate());
			ResultSet rs = st2.executeQuery();
			while (rs.next())
			{
				   System.out.print(rs.getString(1) + ",");
			}
			rs.close();


		}
		st.close();
		db.close();
	}


	static void simplePreparedTest3(String task_executor_type) throws SQLException
	{
		Connection db = DriverManager.getConnection(url, "pdube", "");
		Statement stmt = db.createStatement();
		stmt.executeUpdate("SET citus.enable_repartition_joins TO true;");
		stmt.executeUpdate("SET citus.large_table_shard_count TO 2;");
		stmt.executeUpdate("SET citus.task_executor_type TO '" + task_executor_type + "'" );

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
		st.close();
		db.close();
	}


	static void simplePreparedTest4(String task_executor_type) throws SQLException
	{
		Connection db = DriverManager.getConnection(url, "pdube", "");
		Statement stmt = db.createStatement();
		stmt.executeUpdate("SET citus.enable_repartition_joins TO true;");
		stmt.executeUpdate("SET citus.large_table_shard_count TO 3;");
		stmt.executeUpdate("SET citus.task_executor_type TO '" + task_executor_type + "'" );

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
		st.close();
		db.close();
	}

}

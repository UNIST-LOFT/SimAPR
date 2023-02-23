mvn -Dhttps.protocols=TLSv1.2 compile
mvn -Dhttps.protocols=TLSv1.2 dependency:copy-dependencies
mvn -Dhttps.protocols=TLSv1.2 package
mv target/Avatar-0.0.1-SNAPSHOT.jar target/dependency/


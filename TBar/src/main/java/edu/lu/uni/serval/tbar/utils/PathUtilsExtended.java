package edu.lu.uni.serval.tbar.utils;

import java.util.ArrayList;

public class PathUtilsExtended {

    private static final String SLASH = System.getProperty("file.separator");
    private static final String DOT = ".";

    public static ArrayList<String> getSrcPath(String bugProject) {
        ArrayList<String> path = new ArrayList<String>();

        path.add("/target/classes/");
        path.add("/target/test-classes/");
        path.add("/src/main/java/");
        path.add("/src/test/java/");

        return path;
    }

    public static String getClasspath(String srcPath, String javaFilePath) {
        int pathLength = javaFilePath.length();
        return javaFilePath.substring(srcPath.length(), pathLength - 5).replace(SLASH, DOT);
    }

}

package edu.lu.uni.serval.fixminer;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileReader;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

public class LiteralReader {
	
	public static List<ProjectLiteral> read(String projectName) {
		String fileName;
		if (projectName.startsWith("Math")) {
			fileName = "math";
		} else if (projectName.startsWith("Lang")) {
			fileName = "lang";
		} else if (projectName.startsWith("Chart")) {
			fileName = "chart";
		} else if (projectName.startsWith("Time")) {
			fileName = "time";
		} else if (projectName.startsWith("Mockito")) {
			fileName = "mockito";
		} else {
			fileName = "closure";
		}
		String proName = projectName + "_b";
		List<ProjectLiteral> projectLiterals = readProjectCSV("LocalData/" + fileName + ".csv");
		List<ProjectLiteral> subProjects = selectData(projectLiterals, proName);// JDK8: projectLiterals.stream().filter(x -> x.projectName.equals(proName)).collect(Collectors.toList());
		
		return subProjects;
	}
	
	private static List<ProjectLiteral> selectData(List<ProjectLiteral> projectLiterals, String projectName) {
		List<ProjectLiteral> subProjects = new ArrayList<>();
		for (ProjectLiteral pl : projectLiterals) {
			if (projectName.equals(pl.projectName)) {
				String filePath=pl.file;
				String[] pathArray=filePath.split("/");
				ArrayList<String> internalPath=new ArrayList<>();
				boolean isAdd=false;
				for (String path:pathArray){
					if (!isAdd && path.equals(pl.projectName))
						isAdd=true;
					else if (isAdd)
						internalPath.add(path);
				}
				pl.file="/root/project/FixMiner-APR/buggy/";
				for (String p:internalPath){
					pl.file.concat(p);
					pl.file.concat("/");
				}

				subProjects.add(pl);
			}
		}
		return subProjects;
	}
	
	public static List<ProjectLiteral> readProjectCSV(String fileName) {
		try {
			BufferedReader reader = new BufferedReader(new FileReader(new File(fileName)));
			List<ProjectLiteral> list = new ArrayList<ProjectLiteral>();
			String line = reader.readLine();

			while (line != null) {
				String strArray[] = line.split("\t");

				if (!line.trim().isEmpty()) {
					ProjectLiteral a = null;
					if (strArray.length == 10) {
						a = new ProjectLiteral(strArray[1], strArray[2], strArray[3], strArray[4], strArray[5],
								strArray[6], strArray[7], strArray[8], strArray[9]);
					} else if (strArray.length == 9) {
						a = new ProjectLiteral(strArray[1], strArray[2], strArray[3], strArray[4], strArray[5],
								strArray[6], strArray[7], strArray[8], "");
					} else if (strArray.length == 8) {
						a = new ProjectLiteral(strArray[1], strArray[2], strArray[3], strArray[4], strArray[5],
								strArray[6], strArray[7], "", "");
					} else if (strArray.length == 7) {
						a = new ProjectLiteral(strArray[1], strArray[2], strArray[3], strArray[4], strArray[5],
								strArray[6], "", "", "");
					} else if (strArray.length == 6) {
						a = new ProjectLiteral(strArray[1], strArray[2], strArray[3], strArray[4], strArray[5], "", "",
								"", "");
					} else if (strArray.length == 5) {
						a = new ProjectLiteral(strArray[1], strArray[2], strArray[3], strArray[4], "", "", "", "", "");
					} else if (strArray.length == 4) {
						a = new ProjectLiteral(strArray[1], strArray[2], strArray[3], "", "", "", "", "", "");
					} else {
					}

					if (a != null) list.add(a);
					
					line = reader.readLine();
				}
			}
			reader.close();
			return list;
		} catch (IOException ex) {
			System.out.println("Problems..");
		}
		return null;
	}

}

package edu.lu.uni.serval.fixminer;

public class ProjectLiteral {
	
	public String projectName;
	public String file;
	public String codePath;
	public String className;
	public String extend;
	public String[] stringLiterals;
	public String[] numberLiterals;
	public String[] qualifiedNames;
	public String[] methodInvocation;

	public ProjectLiteral(String name, String file, String packageName, String className, String extend, String sLit,
			String nLit, String mr ,String mi) {
		this.projectName = name;
		this.file = file;
		this.codePath = packageName + "." + className;
		this.extend = extend;
		this.stringLiterals = sLit.split(";");
		this.numberLiterals = nLit.split(";");
        this.qualifiedNames = mr.split(";");
        this.methodInvocation = mi.split(";");
	}
}

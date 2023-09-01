package edu.lu.uni.serval.tbar;

import java.io.File;

import edu.lu.uni.serval.jdt.tree.ITree;

public class SuspCodeNode {

    public File javaBackup;
    public File classBackup;
    public File targetJavaFile;
    public File targetClassFile;
    public int startPos;
    public int endPos;
    public ITree suspCodeAstNode;
    public String suspCodeStr;
    public String suspiciousJavaFile;
    public int buggyLine;

    public double flScore;
    public int rank;

    public SuspCodeNode(File javaBackup, File classBackup, File targetJavaFile, File targetClassFile, int startPos,
            int endPos, ITree suspCodeAstNode, String suspCodeStr, String suspiciousJavaFile, int buggyLine,double flScore,int rank) {
        this.javaBackup = javaBackup;
        this.classBackup = classBackup;
        this.targetJavaFile = targetJavaFile;
        this.targetClassFile = targetClassFile;
        this.startPos = startPos;
        this.endPos = endPos;
        this.suspCodeAstNode = suspCodeAstNode;
        this.suspCodeStr = suspCodeStr;
        this.suspiciousJavaFile = suspiciousJavaFile;
        this.buggyLine = buggyLine;

        this.flScore=flScore;
        this.rank=rank;
    }

    @Override
    public boolean equals(Object obj) {
        if (obj == null) return false;
        if (obj instanceof SuspCodeNode) {
            SuspCodeNode suspN = (SuspCodeNode) obj;
            if (startPos != suspN.startPos) return false;
            if (endPos != suspN.endPos) return false;
            if (suspiciousJavaFile.equals(suspN.suspiciousJavaFile)) return true;
        }
        return false;
    }
}

package kr.ac.unist.apr;

import java.io.File;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import org.eclipse.core.runtime.NullProgressMonitor;
import org.eclipse.jdt.core.dom.AST;
import org.eclipse.jdt.core.dom.ASTParser;
import org.eclipse.jdt.core.dom.ASTVisitor;
import org.eclipse.jdt.core.dom.CompilationUnit;
import org.eclipse.jdt.core.dom.MethodDeclaration;
import org.eclipse.jdt.core.dom.SingleVariableDeclaration;

import edu.lu.uni.serval.utils.FileUtils;

public class MethodFinder extends ASTVisitor{
    private CompilationUnit root;
    private Map<String,Integer[]> functionLocations=new HashMap<>();
    public static Map<String,Map<String,Integer[]>> infos=new HashMap<>();

    public static void parseFiles(String path,String buggyProject){
        System.out.println("Parsing "+path);
        for (File file:new File(path).listFiles()) {
            if (file.isDirectory()) {
                parseFiles(file.getAbsolutePath(),buggyProject);
            }else if (file.getName().endsWith(".java")) {
                MethodFinder finder=new MethodFinder(file.getAbsolutePath());
                finder.root.accept(finder);
                String relPath=file.getAbsolutePath().split(buggyProject)[1].substring(1);
                infos.put(relPath, finder.functionLocations);
            }
        }
    }

    public MethodFinder(String filePath){
        ASTParser parser=ASTParser.newParser(AST.JLS8);
        String source=FileUtils.getCodeFromFile(new File(filePath));
        parser.setSource(source.toCharArray());
        parser.setKind(ASTParser.K_COMPILATION_UNIT);
        root=(CompilationUnit) parser.createAST(new NullProgressMonitor());
    }

    @Override
    public boolean visit(MethodDeclaration node) {
        String funcName=node.getName().getIdentifier();
        int startLine=root.getLineNumber(node.getStartPosition());
        int endLine=root.getLineNumber(node.getStartPosition()+node.getLength());
        List<SingleVariableDeclaration> parameters=node.parameters();
        
        funcName+="[";
        for (int i=0;i<parameters.size();i++) {
            funcName+=parameters.get(i).getType().toString()+" "+parameters.get(i).getName().getIdentifier();
            if (i!=parameters.size()-1) {
                funcName+=",";
            }
        }
        funcName+="]";

        functionLocations.put(funcName, new Integer[]{startLine,endLine});

        return true;
    }

    public Map<String,Integer[]> getFunctionLocations(){
        return functionLocations;
    }
}

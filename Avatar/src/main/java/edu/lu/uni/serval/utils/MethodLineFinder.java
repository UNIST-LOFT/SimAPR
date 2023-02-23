package edu.lu.uni.serval.utils;

import java.io.File;
import java.util.ArrayList;
import java.util.List;

import org.eclipse.core.runtime.NullProgressMonitor;
import org.eclipse.jdt.core.dom.AST;
import org.eclipse.jdt.core.dom.ASTParser;
import org.eclipse.jdt.core.dom.ASTVisitor;
import org.eclipse.jdt.core.dom.CompilationUnit;
import org.eclipse.jdt.core.dom.MethodDeclaration;
import org.eclipse.jdt.core.dom.SingleVariableDeclaration;

import edu.lu.uni.serval.utils.FileUtils;

/**
 * Method line finder.
 * <p>
 * Find method start and end line number in a file.
 * 
 * It will build a AST and find each line number by traversing AST.
 * </p>
 */
public class MethodLineFinder extends ASTVisitor{
    /**
     * Method location.
     */
    static public class FunctionLocation{
        public String funcName;
        public int startLine;
        public int endLine;
        /** List of parameters, for identify overloaded methods. */
        public List<String> params=new ArrayList<>();
    }

    private CompilationUnit root;
    private List<FunctionLocation> functionLocations=new ArrayList<>();
    
    /**
     * Constructor with a source file path.
     * @param filePath source file path
     */
    public MethodLineFinder(String filePath){
        ASTParser parser=ASTParser.newParser(AST.JLS8);
        String source=FileUtils.getCodeFromFile(new File(filePath));
        parser.setSource(source.toCharArray());
        parser.setKind(ASTParser.K_COMPILATION_UNIT);
        root=(CompilationUnit) parser.createAST(new NullProgressMonitor());
    }

    /**
     * Traverse AST, and get method start and end line number.
     * @return list of method locations
     */
    public List<FunctionLocation> getFunctionLocations(){
        root.accept(this);
        return functionLocations;
    }

    /**
     * Visit method declaration, for get start and end line number.
     * <p>
     * Do not call manually this method.
     * </P>
     */
    @Override
    public boolean visit(MethodDeclaration node) {
        FunctionLocation location=new FunctionLocation();
        location.funcName=node.getName().getIdentifier();
        location.startLine=root.getLineNumber(node.getStartPosition());
        location.endLine=root.getLineNumber(node.getStartPosition()+node.getLength());
        List<SingleVariableDeclaration> parameters=node.parameters();
        
        for (SingleVariableDeclaration parameter : parameters) {
            location.params.add(parameter.getType().toString()+" "+parameter.getName().getIdentifier());
        }

        functionLocations.add(location);

        return true;
    }
}

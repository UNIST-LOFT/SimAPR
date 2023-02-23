package edu.lu.uni.serval.json;

import org.apache.commons.io.FileUtils;
import org.eclipse.jdt.core.JavaCore;
import org.eclipse.jdt.core.dom.*;

import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

public class MethodInfoUtils {

    public static MethodBeam validateMethodLineRange(
        int line, String location
    ) throws IOException {
        List<MethodBeam> methods = getAstMethodInfo(location);
        for (MethodBeam method: methods) {
            if (line >= method.start && line <= method.end) {
                return method;
            }
        }
        return null;
    }

    public static MethodBeam getMethodFromLine(int line, String location) throws IOException {
        List<MethodBeam> methods = getAstMethodInfo(location);
        for (MethodBeam method: methods) {
            if (line >= method.start && line <= method.end) {
                return method;
            }
        }
        return null;
    }

    public static List<MethodBeam> getAstMethodInfo(String location) throws IOException {
        ASTParser parser = ASTParser.newParser(AST.JLS8);
        parser.setSource(FileUtils.readFileToString(new File(location), "UTF-8").toCharArray());
        parser.setKind(ASTParser.K_COMPILATION_UNIT);
        parser.setResolveBindings(true);

        Map<String, String> options = JavaCore.getOptions();
        JavaCore.setComplianceOptions(JavaCore.VERSION_1_5, options);
        parser.setCompilerOptions(options);

        final CompilationUnit cu = (CompilationUnit) parser.createAST(null);
        final MethodVisitorAst vis = new MethodVisitorAst(cu);
        cu.accept(vis);

        return vis.methods;
    }

    private static class MethodVisitorAst extends ASTVisitor {

        ArrayList<MethodBeam> methods = new ArrayList<>();
        CompilationUnit cu;

        MethodVisitorAst(CompilationUnit cu) {
            this.cu = cu;
        }

        @Override
        public boolean visit(MethodDeclaration node) {
            String name = node.getName().toString();
            String iden = node.parameters().toString();;
            int start = cu.getLineNumber(node.getStartPosition());
            int end = cu.getLineNumber(node.getStartPosition() + node.getLength());
            methods.add(new MethodBeam(start, end, name, iden));
            return false;
        }
    }

    public static class MethodBeam {

        public final int start;
        public final int end;
        public final String name;
        public final String desc;

        public MethodBeam(int start, int end, String name, String desc) {
            this.start = start;
            this.end = end;
            this.name = name;
            this.desc = desc;
        }
    }
}

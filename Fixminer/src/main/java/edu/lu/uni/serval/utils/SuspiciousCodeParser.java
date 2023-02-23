package edu.lu.uni.serval.utils;

import java.io.File;
import java.util.List;

import org.eclipse.jdt.core.dom.CompilationUnit;

import edu.lu.uni.serval.AST.ASTGenerator;
import edu.lu.uni.serval.AST.ASTGenerator.TokenType;
import edu.lu.uni.serval.jdt.tree.ITree;
import edu.lu.uni.serval.parser.JavaFileParser;
import edu.lu.uni.serval.utils.Checker;
import edu.lu.uni.serval.utils.FileHelper;

/**
 * Parse the suspicious code into an AST.
 * 
 * @author kui.liu
 *
 */
public class SuspiciousCodeParser {

	private File javaFile;
	private CompilationUnit unit = null;
	private ITree suspiciousCodeAstNode = null;
	private String suspiciousCodeStr = null;
	
	public void parseSuspiciousCode(File javaFile, int suspLineNum) {
		this.javaFile = javaFile;
		unit = new JavaFileParser().new MyUnit().createCompilationUnit(javaFile);
		ITree rootTree = new ASTGenerator().generateTreeForJavaFile(javaFile, TokenType.EXP_JDT);
		identifySuspiciousCodeAst(rootTree, suspLineNum);
	}

	private void identifySuspiciousCodeAst(ITree tree, int suspLineNum) {
		List<ITree> children = tree.getChildren();
		
		for (ITree child : children) {
			int startPosition = child.getPos();
			int endPosition = startPosition + child.getLength();
			int startLine = this.unit.getLineNumber(startPosition);
			int endLine = this.unit.getLineNumber(endPosition);
			if (endLine == -1) endLine = this.unit.getLineNumber(endPosition - 1);
			if (startLine <= suspLineNum && suspLineNum <= endLine) {
				if (startLine == suspLineNum || endLine == suspLineNum) {
					if (!isRequiredAstNode(child)) {
						child = traverseParentNode(child);
						if (child == null) break;
					}
					this.suspiciousCodeAstNode = child;
					this.suspiciousCodeStr = readSuspiciousCode();
					break;// FIXME: one code line might contain several statements.
				} else {
					identifySuspiciousCodeAst(child, suspLineNum);
				}
				break;
			} else if (startLine > suspLineNum) {
				break;
			}
		}
	}

	private boolean isRequiredAstNode(ITree tree) {
		int astNodeType = tree.getType();
		if (Checker.isStatement(astNodeType) 
				|| Checker.isFieldDeclaration(astNodeType)
				|| Checker.isMethodDeclaration(astNodeType)
				|| Checker.isTypeDeclaration(astNodeType)) {
			return true;
		}
		return false;
	}

	private ITree traverseParentNode(ITree tree) {
		ITree parent = tree.getParent();
		if (parent == null) return null;
		if (!isRequiredAstNode(parent)) {
			parent = traverseParentNode(parent);
		}
		return parent;
	}

	private String readSuspiciousCode() {
		String javaFileContent = FileHelper.readFile(this.javaFile);
		int startPos = this.suspiciousCodeAstNode.getPos();
		int endPos = startPos + this.suspiciousCodeAstNode.getLength();
		return javaFileContent.substring(startPos, endPos);
	}

	public ITree getSuspiciousCodeAstNode() {
		return suspiciousCodeAstNode;
	}

	public String getSuspiciousCodeStr() {
		return suspiciousCodeStr;
	}
}

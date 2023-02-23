package edu.lu.uni.serval.fixminer.insertTemplate;

import java.util.List;

import edu.lu.uni.serval.jdt.tree.ITree;
import edu.lu.uni.serval.templates.FixTemplate;
import edu.lu.uni.serval.utils.Checker;

/**
 * @author kui.liu
 *
 */
public class StatementMover extends FixTemplate {
	
	/*
	 * MOV Statement.
	 */

	@Override
	public void generatePatches() {
		ITree suspCodeTree = this.getSuspiciousCodeTree();
		int stmtType = suspCodeTree.getType();
		if (Checker.isReturnStatement(stmtType) || Checker.isBreakStatement(stmtType) || Checker.isContinueStatement(stmtType) || Checker.isVariableDeclarationStatement(stmtType)) return;
		ITree parentTree = suspCodeTree.getParent();
		int parentNodeType = parentTree.getType();
		List<ITree> children = parentTree.getChildren();
		int size = children.size();
		if (size == 1) return;
		int s = 0;
		for (ITree child : children) {
			if (Checker.isStatement(child.getType())) s ++;
		}
		if (s == 1) return;

		int index = parentTree.getChildPosition(suspCodeTree);
		int fromIndex = -1, toIndex = -1;
		
		if (Checker.isSwitchStatement(parentNodeType)) {
			if (Checker.isSwitchCase(suspCodeTree.getType())) return;
			
			for (int i = index - 1; i >= 0; i --) {
				if (Checker.isSwitchCase(children.get(i).getType())) {
					fromIndex = i + 1;
					break;
				}
			}
			for (int i = index + 1; i < size; i ++) {
				if (Checker.isSwitchCase(children.get(i).getType())) {
					toIndex = i;
					break;
				}
			}
		} else if (Checker.isTryStatement(parentNodeType)) {
			// the position of the first catch clause.
			if (Checker.isCatchClause(suspCodeTree.getType()) || 
					(Checker.isBlock(suspCodeTree.getType()) && "FinallyBody".equals(suspCodeTree.getLabel()))) return;
			
			for (int i = 0; i < size; i ++) {
				if (Checker.isStatement(children.get(i).getType())) {
					fromIndex = i;
					break;
				}
			}
			for (int i = index + 1; i < size; i ++) {
				ITree peerStmt = children.get(i);
				if (Checker.isCatchClause(peerStmt.getType()) || 
						(Checker.isBlock(peerStmt.getType()) && "FinallyBody".equals(peerStmt.getLabel()))) {
					toIndex = i;
					break;
				}
			}
			
			if (toIndex == -1) toIndex = index + 1;
		} else if (Checker.withBlockStatement(parentNodeType) || Checker.isCatchClause(parentNodeType) || Checker.isMethodDeclaration(parentNodeType)) {
//				|| (Checker.isBlock(parentNodeType) && "FinallyBody".equals(parentTree.getLabel()))) {
//			for (int i = 0; i < size; i ++) {
//				System.out.println(children.get(i).getType());
//				if (Checker.isStatement(children.get(i).getType())) {
//					fromIndex = i;
//					break;
//				}
//			}
			fromIndex = size - s;
			toIndex = size;
		} else return;
		
		if (toIndex == -1 || fromIndex == -1) return;
		index = index - fromIndex;
		List<ITree> peerStmts = children.subList(fromIndex, toIndex);
		exchangeStatementSequence(peerStmts, index);
	}

	private void exchangeStatementSequence(List<ITree> peerStmts, int buggyStmtIndex) {
		for (int index = 0, size = peerStmts.size(); index < size; index ++) {
			if (index < buggyStmtIndex) {
				// move the buggy statement before this statement.
				int startPos = peerStmts.get(index).getPos();
				String code = this.suspJavaFileCode.substring(startPos, suspCodeStartPos);
				String fixedCodeStr1 = this.getSuspiciousCodeStr() + "\n\t" + code;
				this.generatePatch(startPos, suspCodeEndPos, fixedCodeStr1, null);
			} else if (index > buggyStmtIndex){
				// move the buggy statement after this statement.
				int endPos = peerStmts.get(index).getPos() + peerStmts.get(index).getLength();;
				String code = this.suspJavaFileCode.substring(suspCodeEndPos, endPos);
				String fixedCodeStr1 = code  + "\n\t" + this.getSuspiciousCodeStr() + "\n";
				this.generatePatch(suspCodeStartPos, endPos, fixedCodeStr1, "MOVE-BUGGY-STATEMENT");
			}
			
		}
	}

}

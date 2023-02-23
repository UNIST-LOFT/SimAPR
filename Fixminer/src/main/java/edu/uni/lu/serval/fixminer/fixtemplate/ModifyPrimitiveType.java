package edu.uni.lu.serval.fixminer.fixtemplate;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;

import edu.lu.uni.serval.jdt.tree.ITree;
import edu.lu.uni.serval.templates.FixTemplate;
import edu.lu.uni.serval.utils.Checker;
import edu.lu.uni.serval.utils.ListSorter;

/**
 * 
 * @author kui.liu
 *
 */
public class ModifyPrimitiveType extends FixTemplate {
	/*
	 * UPD VariableDeclarationStatement
	 * ---UPD PrimitiveType
	 */
	
	private List<String> primitiveTypes = new ArrayList<>();
	
	public ModifyPrimitiveType() {
		this.primitiveTypes.add("double");
		this.primitiveTypes.add("float");
		this.primitiveTypes.add("long");
		this.primitiveTypes.add("int");
		this.primitiveTypes.add("short");
//		this.primitiveTypes.add("char");
		this.primitiveTypes.add("byte");
//		this.primitiveTypes.add("boolean");
	}

	@Override
	public void generatePatches() {
		ITree suspCodeAst = this.getSuspiciousCodeTree();
		
		if (Checker.isVariableDeclarationStatement(suspCodeAst.getType())) {
			ITree typeTree = null;
			List<ITree> children = suspCodeAst.getChildren();
			for (ITree child : children) {
				if (Checker.isModifier(child.getType())) continue;
				typeTree = child;
				break;
			}
			String typeStr = typeTree.getLabel();
			
			if (this.primitiveTypes.contains(typeStr)) {
				int index = suspCodeAst.getChildPosition(typeTree) + 1;
				List<String> variables = new ArrayList<>();
				for (int size = children.size(); index < size; index ++) {
					variables.add(children.get(index).getChildren().get(0).getLabel());
				}
				
				List<ITree> stmts = suspCodeAst.getParent().getChildren();
	    		ITree lastStmt = null;
	    		boolean isFollowingStmt = false;
	    		List<Integer> positionsList1 = new ArrayList<>();
	    		System.out.println();
	    		for (int i = 0, size = stmts.size(); i < size; i ++) {
	    			ITree stmt = stmts.get(i);
	    			if (isFollowingStmt) {
	    				List<Integer> posList = new ArrayList<>();
	    				identifySameTypes(stmt, typeStr, variables, (i == size - 1 ? null : stmts.subList(i + 1, size)), posList);
	        			if (posList.size() > 0) {
	        				lastStmt = stmt;
	        				positionsList1.addAll(posList);
	        			}
	    			} else if (stmt == suspCodeAst) {
	    				isFollowingStmt = true;
	    			}
	    		}
				
				int typeStartPos = typeTree.getPos();
				int typeEndPos = typeStartPos + typeTree.getLength();
				String codePart1 = this.getSubSuspiciouCodeStr(suspCodeStartPos, typeStartPos);
				String codePart2 = this.getSubSuspiciouCodeStr(typeEndPos, suspCodeEndPos);
				for (String primitiveType : this.primitiveTypes) {
					if (primitiveType.equals(typeStr)) continue;
					String fixedCodeStr1 = codePart1 + primitiveType + codePart2;
					this.generatePatch(fixedCodeStr1);
					
					if (lastStmt != null) {
						String patch = fixedCodeStr1;
		    			int endPos = this.suspCodeEndPos;
//		    			positionsList = positionsList.stream().distinct().collect(Collectors.toList());// JDK 1.8
		    			List<Integer> positionsList = new ArrayList<>(new HashSet<>(positionsList1));
		    			ListSorter<Integer> sorter = new ListSorter<Integer>(positionsList);
		    			positionsList = sorter.sortAscending();
		    			int s = positionsList.size();
		    			for (int i = 0; i < s; i ++) {
		    				int prevPos = i == 0 ? endPos : (positionsList.get(i - 1) + typeStr.length());
		    				int currPos = positionsList.get(i);
		    				patch += this.getSuspJavaFileCode().substring(prevPos, currPos) + primitiveType;
						}
		    			int prevPos = positionsList.get(s - 1) + typeStr.length();
		    			endPos = lastStmt.getPos() + lastStmt.getLength();
		    			patch += this.getSuspJavaFileCode().substring(prevPos, endPos);
		    			this.generatePatch(endPos, endPos, patch, "");
		    		}
				}
			}
		}
	}
	
	private void identifySameTypes(ITree stmt, String oldType, List<String> variables, List<ITree> peerStmts, List<Integer> posList) {
		if (Checker.isVariableDeclarationStatement(stmt.getType())) {
			ITree dataType = null;
			String variable = null;
			List<ITree> children = stmt.getChildren();
			for (ITree child : children) {
				int type = child.getType();
				if (Checker.isModifier(type)) continue;
				if (Checker.isVariableDeclarationFragment(type)) {//VariableDeclarationFragment
					variable = child.getChildren().get(0).getLabel();
					break;
				} else {
					dataType = child;
				}
			}
			if (dataType != null && dataType.getLabel().equals(oldType)) {
				if (isCorelatedStmt(stmt, variables, 60, peerStmts, posList, oldType)) {
					posList.add(dataType.getPos());
					variables.add(variable);
				}
			}
		} else if (Checker.withBlockStatement(stmt.getType())) {
			List<ITree> children = stmt.getChildren();
			for (int index = 0, size = children.size(); index < size; index ++) {
				ITree child = children.get(index);
				if (Checker.isStatement(child.getType())) {
					identifySameTypes(child, oldType, variables, (index == size - 1 ? null : children.subList(index + 1, size)), posList);
				}
			}
		}
	}

	private boolean isCorelatedStmt(ITree stmt, List<String> variables, int stmtType, List<ITree> peerStmts, List<Integer> posList, String oldType) {
		List<ITree> children = stmt.getChildren();
		boolean isCorelatedStmt = false;
		for (int index = 0, size = children.size(); index < size; index ++) {
			ITree child = children.get(index);
			// variables in stmt are int variable list.
			int type = child.getType();
			if (Checker.isSimpleName(type)) {
				String variable = child.getLabel();
				if (variables.contains(variable)) {
					isCorelatedStmt = true;
				} else if (Checker.isVariableDeclarationStatement(stmtType)) {// VariableDeclarationStatement
					variables.add(variable);
				}
			} else if (Checker.isComplexExpression(type)) {
				isCorelatedStmt = isCorelatedStmt(child, variables, stmtType, null, posList, oldType);
				if (isCorelatedStmt) return isCorelatedStmt;
			} else if (Checker.isStatement(type)) {
				identifySameTypes(child, oldType, variables, (index == size - 1 ? null : children.subList(index + 1, size)), posList);
			}
		}
		if (peerStmts != null) {
			for (ITree peerStmt : peerStmts) {
				isCorelatedStmt = isCorelatedStmt(peerStmt, variables, stmtType, null, posList, oldType);
				if (isCorelatedStmt) return isCorelatedStmt;
			}
		}
		return isCorelatedStmt;
	}

}

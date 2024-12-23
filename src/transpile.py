import ast
import syside
from enum import Enum
from typing import Tuple

global returnAst
returnAst = None

class ExpType(Enum):
  UnaryOp = 1
  BinOp = 2
  Compare = 3

# sysml operator, number of operands to python operator, and expression type
operator_mapping = {
  ("Minus", 1): (ast.USub(), ExpType.UnaryOp),
  ("Plus", 1): (ast.UAdd(), ExpType.UnaryOp),
  ("Minus", 2): (ast.Sub(), ExpType.BinOp),
  ("Plus", 2): (ast.Add(), ExpType.BinOp),
  ("Multiply", 2): (ast.Mult(), ExpType.BinOp),
  ("Divide", 2): (ast.Div(), ExpType.BinOp),  
  ("Equals", 2): (ast.Eq(), ExpType.Compare),
  ("NotEquals", 2): (ast.NotEq(), ExpType.Compare),
  ("Less", 2): (ast.Lt(), ExpType.Compare),
  ("LessEqual", 2): (ast.LtE(), ExpType.Compare),
  ("Greater", 2): (ast.Gt(), ExpType.Compare),
  ("GreaterEqual", 2): (ast.GtE(), ExpType.Compare),
}

# convert sysml operator to python operator
def convOperator(sysmlOp: syside.Operator, opCount: int) \
                                                -> Tuple[ast.AST, Enum]:
  try:
    return operator_mapping[(sysmlOp, opCount)]
  except KeyError:
    raise ValueError(f"Operator {sysmlOp},{opCount} not supported.")

# Mapping of SysML types to Python types
type_mapping = {
    "Integer": "int",
    "Boolean": "bool",
    "String": "str",
    "Rational": "float"
}
# convert sysml datatype to python datatype
def convType(sysmlType: syside.Type) -> str:
  try:
    return type_mapping[sysmlType.name]
  except KeyError:
    raise ValueError(f"Type {sysmlType.name} not supported.")

# recursively traverse sysml ast nodes, outputing python ast nodes
def traverseNode(node: syside.AstNode, level: int = 0) -> ast.AST:
  global returnAst
  
  # ---------LiteralInteger-----------
  if node.try_cast(syside.LiteralInteger):
    litInt = node.cast(syside.LiteralInteger)
    print("  " * level, "LiteralInteger...")
    return(ast.Constant(value=litInt.value))
  
  # ---------LiteralString-----------
  elif node.try_cast(syside.LiteralString):
    litStr = node.cast(syside.LiteralString)
    print("  " * level, "LiteralString...")
    return(ast.Constant(value=litStr.value))
  
  # ---------LiteralBoolean-----------
  elif node.try_cast(syside.LiteralBoolean):
    litBool = node.cast(syside.LiteralBoolean)
    print("  " * level, "LiteralBoolean...")
    return(ast.Constant(value=litBool.value)) 
  
  # ---------LiteralRational-----------
  elif node.try_cast(syside.LiteralRational):
    litRat = node.cast(syside.LiteralRational)
    print("  " * level, "LiteralRational...")
    return(ast.Constant(value=litRat.value))
  
  # ---------IfActionUsage-----------
  elif node.try_cast(syside.IfActionUsage):
    ifAction = node.cast(syside.IfActionUsage)
    print("  " * level, "IfAction...")
    nlevel = level + 1
    if ifAction.parameters.at(2) == None:
      return ast.If(test=traverseNode(ifAction.parameters[0], nlevel),
                    body=traverseNode(ifAction.parameters[1], nlevel),
                    orelse=[])       
    else:
      return ast.If(test=traverseNode(ifAction.parameters[0], nlevel),
                    body=traverseNode(ifAction.parameters[1], nlevel),
                    orelse=traverseNode(ifAction.parameters[2], nlevel))
  
  # ---------TerminateActionUsage-----------
  elif node.try_cast(syside.TerminateActionUsage):
    print("  " * level, "Terminate...")
    return(returnAst)
  
  # ---------FeatureReferenceExpression-----------
  elif node.try_cast(syside.FeatureReferenceExpression):
    featRef = node.cast(syside.FeatureReferenceExpression)
    print("  " * level, "FeatureReferenceExpression...")
    return(ast.Name(id=featRef.referent.name,
                    ctx=ast.Load()))
  
  # ---------OperatorExpression-----------
  elif node.try_cast(syside.OperatorExpression):
    ops=[]
    comparators=[]
    opExp = node.cast(syside.OperatorExpression)
    print("  " * level, "OperatorExpression...")
    nlevel = level + 1
    opCount = opExp.operands.count()
    (op, expType) = convOperator(opExp.operator.name, opCount)
    if expType == ExpType.Compare:
      ops.append(op)
      left = traverseNode(opExp.operands[0], nlevel)
      comparators.append(traverseNode(opExp.operands[1], nlevel))
      return(ast.Compare(left=left,
                         ops=ops,
                         comparators=comparators))
    elif expType == ExpType.UnaryOp:
      return(ast.UnaryOp(op=op,
                         operand=traverseNode(opExp.operands[0], nlevel)))
    elif expType == ExpType.BinOp:
      return(ast.BinOp(left=traverseNode(opExp.operands[0], nlevel),
                       op=op,
                       right=traverseNode(opExp.operands[1], nlevel)))
    else:
      assert False, f"Expression {expType} not supported."

  # ---------AssignmentActionUsage-----------
  elif node.try_cast(syside.AssignmentActionUsage):
    print("  " * level, "AssignentActionUsage...")
    assignUsage = node.cast(syside.AssignmentActionUsage)
    nlevel = level + 1
    targets=[]
    targets.append(ast.Name(id=assignUsage.referent.name,
                            ctx=ast.Store()))
    value=traverseNode(assignUsage.value_expression, nlevel)
    return(ast.Assign(targets=targets,
                      value=value))
  
  # ---------ActionUsage-----------
  elif node.try_cast(syside.ActionUsage):
    features=[]
    print("  " * level, "ActionUsage...")
    actUsage = node.cast(syside.ActionUsage)
    nlevel = level + 1
    for feature in actUsage.owned_features:
      features.append(traverseNode(feature, nlevel))
    return(features)
  
  else:
    assert False, f"Node Type {node} not supported."

# transform sysml action to python function
def transformAction(func: syside.ActionDefinition) -> ast.FunctionDef:
  args=[]
  returns=None
  actions=[]
  global returnAst
 
  # parse input arguments and return type
  for param in func.parameters:
    if param.direction == syside.FeatureDirectionKind.In: 
      args.append(ast.arg(arg=param.name,
                          annotation=ast.Name(id=convType(param.types[0]), 
                                              ctx=ast.Load())))
    elif param.direction == syside.FeatureDirectionKind.Out:
      returns=ast.Name(id=convType(param.types[0]),
                                   ctx=ast.Load())
      returnAst = ast.Return(value=ast.Name(id=param.name,
                                            ctx=ast.Load()))
    else:
      assert False, f"Paramerter direction {param.direction} not supported."
  
  # parse actions of function
  for action in func.owned_actions:
    actions.append(traverseNode(action, 0))
  
  return ast.FunctionDef(name=func.name, 
                         args=ast.arguments(posonlyargs=[], 
                                            args=args,
                                            kwonlyargs=[],
                                            defaults=[]),
                         body=actions,
                         decorator_list=[],
                         returns=returns)

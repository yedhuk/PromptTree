import prompttree as pt                                                                                                                                          
                
# 1. Create engine                                                                                                                                               
engine = pt.PromptTree(storage="./.prompttree-test")
                                                                                                                                                                
# 2. Save a node and label it
node = engine.save("Analyze {{component}} in drawing {{drawing}}", label="prod")                                                                                 
print(node.id)                                                                                                                                                   

# 3. Render it                                                                                                                                                   
print(engine.get_prompt("prod", vars={"component": "valve", "drawing": "GAD_05"}))
                                                                                                                                                                
# 4. List nodes and labels
print(engine.list_nodes())                                                                                                                                       
print(engine.get_labels())                                                                                                                                       

# 5. Lock and unlock                                                                                                                                             
# engine.lock("my-secret-key")
# print(engine.get_node(node.id).metadata.encrypted)  # True                                                                                                       

# engine2 = pt.PromptTree(storage="./.prompttree-test", key="my-secret-key")                                                                                       
# print(engine2.get_prompt("prod", vars={"component": "valve", "drawing": "GAD_05"}))
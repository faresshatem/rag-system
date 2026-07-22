from langchain_core.messages import convert_to_messages
msgs = [("user", "hello"), ("assistant", "world")]
print(convert_to_messages(msgs))

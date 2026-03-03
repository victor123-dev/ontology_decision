import contextvars

# 定义全局上下文变量
thread_id_var = contextvars.ContextVar('thread_id', default=None)
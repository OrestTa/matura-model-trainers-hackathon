import ctypes,ctypes.util,errno,json,socket,sys,os
lib=ctypes.CDLL(ctypes.util.find_library("seccomp"),use_errno=True)
lib.seccomp_init.argtypes=[ctypes.c_uint32];lib.seccomp_init.restype=ctypes.c_void_p
lib.seccomp_syscall_resolve_name.argtypes=[ctypes.c_char_p];lib.seccomp_syscall_resolve_name.restype=ctypes.c_int
lib.seccomp_rule_add.argtypes=[ctypes.c_void_p,ctypes.c_uint32,ctypes.c_int,ctypes.c_uint]
lib.seccomp_load.argtypes=[ctypes.c_void_p]
ctx=lib.seccomp_init(0x7fff0000)
for name in (b"connect",):
 assert lib.seccomp_rule_add(ctx,0x00050000|errno.EPERM,lib.seccomp_syscall_resolve_name(name),0)==0
class Cmp(ctypes.Structure):
 _fields_=[("arg",ctypes.c_uint),("op",ctypes.c_int),("a",ctypes.c_uint64),("b",ctypes.c_uint64)]
lib.seccomp_rule_add_array.argtypes=[ctypes.c_void_p,ctypes.c_uint32,ctypes.c_int,ctypes.c_uint,ctypes.POINTER(Cmp)]
cmp=Cmp(1,7,15,2)
assert lib.seccomp_rule_add_array(ctx,0x00050000|errno.EPERM,lib.seccomp_syscall_resolve_name(b"socket"),1,ctypes.byref(cmp))==0
assert lib.seccomp_load(ctx)==0
proof={}
try:socket.create_connection(("1.1.1.1",443),timeout=1)
except OSError as e:proof["outbound_tcp_denied"]=e.errno==errno.EPERM
try:socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
except OSError as e:proof["udp_socket_denied"]=e.errno==errno.EPERM
assert all(proof.values()) and len(proof)==2
open(sys.argv[1],"w").write(json.dumps(proof))
os.execv(sys.argv[2],sys.argv[2:])

import paramiko
import numpy as np
import os

class Machine_topo():
    def __init__(self, id, logi_core_num, phys_core_num):
        self.id = id
        self.HT = False
        self.logi_core_num = logi_core_num
        self.phys_core_num = phys_core_num
        self.socket_list = []

    def get_sib(self, logi_id):
        for i in range(len(self.socket_list)):
            for j in range(len(self.socket_list[i].physical_core_list)):
                for k in range(len(cpu_topo_tree.socket_list[i].physical_core_list[j].logical_core_list)):
                    logi_core = self.socket_list[i].physical_core_list[j].logical_core_list[k]
                    if logi_core.id == logi_id:
                        return logi_core.sib

class Socket_topo():
    def __init__(self, id):
        self.id = id
        self.physical_core_list = []

class Phys_core_topo():
    def __init__(self, id):
        self.id = id
        self.logical_core_list = []

class Logi_core_topo():
    def __init__(self, id, sib):
        self.id = id
        self.sib = sib

class SSH_Client():
    def __init__(self, hostname, username, password, timeout, port=22):
        self.hostname = hostname
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.client.connect(hostname, port, username, password)
        self.timeout = timeout

    def run_cmd(self, cmd):
        """
        远程执行CMD
        :param cmd:
        :return:
        """
        std_in, std_out, std_err = self.client.exec_command(cmd)
        return std_out.read().decode('utf-8'), std_err.read().decode('utf-8')

def range_cpuset2list(range_str):
    """
    将范围型cpuset的string转换为list
    比如将“0-2”转换为[0, 1, 2];
    "0"转换为[0]
    :param range_str:
    :return:
    """
    result = set()
    if '-' in range_str:
        range_temp = range_str.split('-')
        range_min = int(range_temp[0])
        range_max = int(range_temp[1])
        for i in range(range_min, range_max + 1):
            result.add(i)
    else:
        result.add(int(range_str))
    return sorted(list(result))


def str2list(set_str):
    """
    将“0,6”转换为[0,6];
    将“0-2”转换为[0, 1, 2];
    将“0-2,6-8”转换为[0, 1, 2, 6, 7, 8];
    :param set_str:
    :return:
    """
    result = set()
    if ',' in set_str:
        if '-' in set_str:
            temp_range_list = set_str.split(',')
            for range_str in temp_range_list:
                for i in range_cpuset2list(range_str):
                    result.add(int(i))
        else:
            temp_enum_list = set_str.split(',')
            for i in temp_enum_list:
                result.add(int(i))
    else:
        for i in range_cpuset2list(set_str):
            result.add(int(i))
    return sorted(list(result))


def get_raw_l1_arr(ssh_client, logical_core_num):
    """
    获得原始的L1缓存共享矩阵
    :return:
    """
    L1_logical_core_list = []
    req = 'cat /sys/devices/system/cpu/cpu{}/cache/index0/shared_cpu_list'
    for i in range(logical_core_num):
        set_str = ssh_client.run_cmd(req.format(str(i)))[0][:-1]
        # print(set_str)
        cover_logi_core = str2list(set_str)
        L1_logical_core_list.append(cover_logi_core)
    L1_logical_core_arr = np.array(L1_logical_core_list)

    return L1_logical_core_arr


def get_raw_l3_arr(ssh_client, logical_core_num):
    """
    获得原始的L3缓存共享矩阵
    :return:
    """
    L3_logical_core_list = []
    req = 'cat /sys/devices/system/cpu/cpu{}/cache/index3/shared_cpu_list'
    for i in range(logical_core_num):
        set_str = ssh_client.run_cmd(req.format(str(i)))[0][:-1]
        # print(set_str)
        cover_logi_core = str2list(set_str)
        L3_logical_core_list.append(cover_logi_core)
    L3_logical_core_arr = np.array(L3_logical_core_list)

    return L3_logical_core_arr


def get_raw(ssh_client):
    """
    获得CPU架构原始数据，返回字典形式的原始返回值：
    （1）logical_core_num： CPU的逻辑核心数
    （2）physical_core_num：CPU的物理核心数
    （3）L1cache_arr：共享L1缓存的逻辑核心矩阵
    （4）L3cache_arr：共享L3缓存的逻辑核心矩阵
    :return:
    """
    cpu_topo_raw = {}
    cpu_topo_raw['m_id'] = ssh_client.hostname
    cpu_topo_raw['physical_core_num'] = int(ssh_client.run_cmd('cat /proc/cpuinfo | grep "core id" | sort | uniq | wc -l')[0][:-1])
    cpu_topo_raw['logical_core_num'] = int(ssh_client.run_cmd('cat /proc/cpuinfo | grep "processor" | wc -l')[0][:-1])
    cpu_topo_raw['L1cache_arr'] = get_raw_l1_arr(ssh_client, cpu_topo_raw['logical_core_num'])
    cpu_topo_raw['L3cache_arr'] = get_raw_l3_arr(ssh_client, cpu_topo_raw['logical_core_num'])

    return cpu_topo_raw


def build_cpu_topo_tree(cpu_topo_raw):
    """
    建立多叉树结构
    :param cpu_topo_raw:
    :return:
    """
    m_id = cpu_topo_raw['m_id']
    logical_core_num = cpu_topo_raw['logical_core_num']
    physical_core_num = cpu_topo_raw['physical_core_num']
    L1cache_arr = cpu_topo_raw['L1cache_arr']
    L3cache_arr = cpu_topo_raw['L3cache_arr']

    # print(logical_core_num)
    # print(physical_core_num)

    # 对数组做去重处理
    L1cache_arr = np.unique(L1cache_arr, axis=0)
    L3cache_arr = np.unique(L3cache_arr, axis=0)
    print(L1cache_arr)
    print(L3cache_arr)

    # 建立根节点（机器节点）
    machine = Machine_topo(m_id, logical_core_num, physical_core_num)

    # 判断是否开启了超线程机制
    if logical_core_num == physical_core_num:
        machine.HT = False
    else:
        machine.HT = True

    # 获得socket数量
    socket_num = L3cache_arr.shape[0]

    # 记录logi_core是否被访问过
    logi_visited = np.zeros((logical_core_num))

    # 开始建立多叉树
    for i in range(socket_num):

        # 建立socket节点
        socket = Socket_topo(i)

        logi_core_list = L3cache_arr[i]
        for logi_core in logi_core_list:

            # 用于存储同物理核的逻辑核心对
            sib_pair = []
            for j in range(physical_core_num):
                if logi_core in list(L1cache_arr[j, :]) and int(logi_visited[logi_core]) is 0:
                    if machine.HT:
                        sib_pair.append(L1cache_arr[j, 0])
                        sib_pair.append(L1cache_arr[j, 1])
                        logi_visited[sib_pair[0]] = 1
                        logi_visited[sib_pair[1]] = 1
                    else:
                        sib_pair.append(L1cache_arr[j, 0])
                        logi_visited[sib_pair[0]] = 1
            # print(sib_pair)

            if len(sib_pair) is not 0 and logi_visited[logi_core] is not -1:
                phys_core = Phys_core_topo(logi_core)
                if machine.HT:
                    phys_core.logical_core_list.append(Logi_core_topo(sib_pair[0], sib_pair[1]))
                    phys_core.logical_core_list.append(Logi_core_topo(sib_pair[1], sib_pair[0]))
                    socket.physical_core_list.append(phys_core)
                    logi_visited[sib_pair[0]] = -1
                    logi_visited[sib_pair[1]] = -1
                else:
                    phys_core.logical_core_list.append(Logi_core_topo(sib_pair[0], None))
                    socket.physical_core_list.append(phys_core)
                    logi_visited[sib_pair[0]] = -1

        machine.socket_list.append(socket)
    return machine


if __name__ == '__main__':
    # ip = '192.168.0.101'
    # username = 'root'
    # pwd = '123'

    # ip = '192.168.0.205'
    # username = 'root'
    # pwd = 'root123'

    ip = '192.168.0.206'
    username = 'root'
    pwd = 'root123'

    force_overwrite = False

    temp_raw_path = ip + '_cpu_topo_raw.npy'
    tree_path = ip + '_cpu_topo_tree.npy'

    ssh_client = SSH_Client(ip, username, pwd, 2)

    if os.path.isfile(tree_path) and not force_overwrite:
        print('读取CPU拓扑树信息。。。')
        cpu_topo_tree = np.load(tree_path, allow_pickle=True).item()

    else:
        if os.path.isfile(temp_raw_path) and not force_overwrite:
            print('读取原始底层信息。。。')
            cpu_topo_raw = np.load(temp_raw_path, allow_pickle=True).item()
        else:
            print('远程收集底层信息。。。')
            cpu_topo_raw = get_raw(ssh_client)
            # 保存收集信息
            np.save(temp_raw_path, cpu_topo_raw)

        print('信息收集完毕，开始建树操作...')
        cpu_topo_tree = build_cpu_topo_tree(cpu_topo_raw)
        # 保存树结构
        np.save(tree_path, cpu_topo_tree)

    # 获得某逻辑核心的兄弟节点
    print(cpu_topo_tree.get_sib(0))


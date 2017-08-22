from utils import enter_depend_test, STEPS, RESULT, SETUP
enter_depend_test()

from depend_test_framework.core import Action, ParamsRequire, Provider, Consumer, CheckPoint, TestObject, Mist, MistDeadEndException, MistClearException


def host_hugepage_config(params, env):
    """
    set environment on host
    """
    if params.hugetlbfs_mount is None:
        params.hugetlbfs_mount = '/dev/hugepages'

    params.doc_logger.info(SETUP + '# cat /etc/libvirt/qemu.conf\n' + \
                               'hugetlbfs_mount = "%s"\n' % params.hugetlbfs_mount)
    params.doc_logger.info("""
    # service libvirtd restart
    Stopping libvirtd daemon: [ OK ]
    Starting libvirtd daemon: [ OK ]
        """)

    if params.hugetlbfs_mount is not '':
        params.doc_logger.info("""
    Then guest memory backing files will be put in %s/libvirt/qemu/.
    #mount -t hugetlbfs hugetlbfs %s 

    2> reserve memory for huge pages, e.g:
    #sysctl vm.nr_hugepages=600
            """ % (params.hugetlbfs_mount, params.hugetlbfs_mount))
    else:
        # We need do some other things after env reached or require
        start = [Provider('$guest_name.active', Provider.CLEAR),
                 Provider('$guest_name.hugepage', Provider.SET)]
        end = [Provider('$guest_name.active', Provider.SET),
               Provider('$guest_name.hugepage', Provider.SET)]
        def mist_host_hugepage(func, params, env):
            params.doc_logger.info(STEPS + "# virsh start %s" % params.guest_name)
            params.doc_logger.info(RESULT + "error: Failed to start domain %s" % params.guest_name)
            params.doc_logger.info("error: internal error hugepages are disabled by administrator config")
            raise MistDeadEndException()
        return Mist(start, end, mist_host_hugepage)


def guest_hugepage_settings(params, env):
    """
    set the huegapege xml element in guest xml
    """
    if params.pagesize == 'default':
        xml = """
              <memoryBacking>
              <hugepages/>
              </memoryBacking>
              """
    elif params.pagesize:
        xml = """
        <memoryBacking>
        <hugepages>
        <page size='%s' unit='KiB'/>
        </hugepages>
        </memoryBacking>
        """ % params.pagesize 
    params.doc_logger.info(STEPS + """
        Add the below xml in guest:
        %s
        """ % xml)


def check_hugepage_cmdline(params, env):
    """
    Check the qemu command line
    """
    params.doc_logger.info(STEPS + "# ps aux|grep %s" % params.guest_name)
    if params.pagesize != '4':
        params.doc_logger.info(RESULT + "...-mem-path %s/libvirt/qemu..." % params.hugetlbfs_mount)
    else:
        params.doc_logger.info(RESULT + "There is no ...-mem-path %s/libvirt/qemu..." % params.hugetlbfs_mount)


def set_mem_backend_xml(params, env):
    """
    """
    DATA = """
prepare a guest have xml with different element which will effect by memory backing:

...
    <numa>
      <cell id='0' cpus='0-2' memory='524288' unit='KiB' memAccess='shared'/>
      <cell id='1' cpus='3-5' memory='524288' unit='KiB'/>
    </numa>
...
    <memory model='dimm' access='private'>
      <target>
        <size unit='KiB'>524287</size>
        <node>0</node>
      </target>
      <address type='dimm' slot='0'/>
    </memory>
    <memory model='dimm'>
      <target>
        <size unit='KiB'>524287</size>
        <node>0</node>
      </target>
      <address type='dimm' slot='1'/>
    </memory>
    <memory model='nvdimm' access='shared'>
      <source>
        <path>/tmp/nvdimm</path>
      </source>
      <target>
        <size unit='KiB'>524288</size>
        <node>1</node>
        <label>
          <size unit='KiB'>128</size>
        </label>
      </target>
      <address type='dimm' slot='2'/>
    </memory>
    <memory model='nvdimm'>
      <source>
        <path>/tmp/nvdimm</path>
      </source>
      <target>
        <size unit='KiB'>524288</size>
        <node>1</node>
        <label>
          <size unit='KiB'>128</size>
        </label>
      </target>
      <address type='dimm' slot='3'/>
    </memory>
...

    """


def set_mem_lock_xml(params, env):
    """
    Add the mlock in the xml
    """
    params.doc_logger.info(STEPS + """
    Add the locked element in guest xml:
    <memoryBacking>
    ...
      *<locked/>*
    ...
    </memoryBacking>
        """)


def verify_mem_lock(params, env):
    """
    Check mlock function
    """
    if env.get_data('$guest_name.memtune') and params.memtune.hardlimit:
        value = int(params.memtune.hardlimit) * 1024 * 1024
    else:
        value = 'unlimited'

    params.doc_logger.info(STEPS + """
    # prlimit -p `pidof qemu-kvm`
        """)
    params.doc_logger.info(RESULT + """
    RESOURCE   DESCRIPTION                              SOFT       HARD UNITS
    ...
    MEMLOCK    max locked-in-memory address space %s %s bytes
    ...
        """ % (value, value))


def set_nosharepage_xml(params, env):
    """
    Add no sharepage element in guest xml
    """
    params.doc_logger.info(STEPS + """
    <memoryBacking>
    ...
      *<nosharepages/>*
    ...
    </memoryBacking>
        """)


def verify_nosharepage(params, env):
    """
    Verify nosharepage function
    """
    params.doc_logger.info(STEPS + "# ps aux|grep %s" % params.guest_name)
    params.doc_logger.info(RESULT + "...mem-merge=off...")


def virsh_memtune(params, env):
    """
    Use virsh memtune to set memtune of guest
    """
    options = ""
    if params.memtune.hardlimit:
        options += "--hard-limit %d " % params.memtune.hardlimit
    if params.memtune.softlimit:
        options += "--soft-limit %d " % params.memtune.softlimit
    if params.memtune.swaphardlimit:
        options += "--swap-hard-limit %d " % params.memtune.swaphardlimit
    params.doc_logger.info(STEPS + "# virsh memtune %s %s --live" % (params.guest_name, options))
    params.doc_logger.info(RESULT + "")
    if params.restart_libvirtd:
        start = [Provider('$guest_name.active', Provider.SET),
                 Provider('$guest_name.memtune', Provider.SET)]
        end = [Provider('$guest_name.active', Provider.SET),
                 Provider('$guest_name.memtune', Provider.SET)]

        def restart_and_memtune(func, params, env):
            params.doc_logger.info(STEPS + """
        # service libvirtd restart
        Stopping libvirtd daemon: [ OK ]
        Starting libvirtd daemon: [ OK ]
                """)
            func(params, env)
            raise MistClearException

        return Mist(start, end, restart_and_memtune)


def virsh_memtune_conf(params, env):
    """
    Use virsh memtune to set memtune of guest conf
    """
    options = ""
    if params.memtune.hardlimit:
        options += "--hard-limit %d " % params.memtune.hardlimit
    if params.memtune.softlimit:
        options += "--soft-limit %d " % params.memtune.softlimit
    if params.memtune.swaphardlimit:
        options += "--swap-hard-limit %d " % params.memtune.swaphardlimit
    params.doc_logger.info(STEPS + "# virsh memtune %s %s --config" % (params.guest_name, options))
    params.doc_logger.info(RESULT + "")


def verify_memtune_cgroup(params, env):
    """
    Check the memtune in the cgroup level
    """
    params.doc_logger.info(STEPS + "# cgget -g memory /machine.slice/machine-qemu\\x2d%s.scope" % (params.guest_name))
    params.doc_logger.info(RESULT)
    if params.memtune.hardlimit:
        params.doc_logger.info("""
    memory.limit_in_bytes: %d
            """ % (params.memtune.hardlimit * 1024))
    if params.memtune.softlimit:
        params.doc_logger.info("""
    memory.soft_limit_in_bytes: %d
            """ % (params.memtune.softlimit * 1024))
    if params.memtune.swaphardlimit:
        params.doc_logger.info("""
    memory.memsw.limit_in_bytes: %d
            """ % (params.memtune.swaphardlimit * 1024))


def verify_memtune_xml(params, env):
    """
    Check the memtune in the guest xml
    """
    params.doc_logger.info(STEPS + "# virsh dumpxml %s" % (params.guest_name))
    params.doc_logger.info(RESULT)
    if params.memtune.hardlimit:
        params.doc_logger.info("""
    <hard_limit unit='KiB'>%d</hard_limit>
            """ % params.memtune.hardlimit)
    if params.memtune.softlimit:
        params.doc_logger.info("""
    <soft_limit unit='KiB'>%d</soft_limit>
            """ % params.memtune.softlimit)
    if params.memtune.swaphardlimit:
        params.doc_logger.info("""
    <swap_hard_limit unit='KiB'>%d</swap_hard_limit>
            """ % params.memtune.swaphardlimit)

def set_memballoon_xml(params, env):
    """
    Set the memballon device in guest xml
    """
    params.doc_logger.info(STEPS + """
    <memballoon model='%s'>
    </memballoon>
        """ % params.memballoon.model)

    if params.memballoon.model == 'none':
        start = [Provider('$guest_name.active', Provider.SET)]
        end = [Provider('$guest_name.active', Provider.SET),
                 Provider('$guest_name.curmem', Provider.SET)]

        def restart_and_memtune(func, params, env):
            params.doc_logger.info(STEPS + "# virsh setmem %s %d" % (params.guest_name, params.curmem))
            params.doc_logger.info(RESULT + "error: Requested operation is not valid: Unable to change memory of active domain without the balloon device and guest OS balloon driver")
            raise MistDeadEndException

        return Mist(start, end, restart_and_memtune)

# TODO maybe we can merge this two to one func ?
def hot_set_guest_mem(params, env):
    """
    Use virsh setmem to change the running guest memory size
    """
    params.doc_logger.info(STEPS + "# virsh setmem %s %d --live" % (params.guest_name, params.curmem))
    params.doc_logger.info(RESULT)

def cold_set_guest_mem(params, env):
    """
    Use virsh setmem to change the guest memory size in xml
    """
    params.doc_logger.info(STEPS + "# virsh setmem %s %d --config" % (params.guest_name, params.curmem))
    params.doc_logger.info(RESULT)

def verify_setmem_in_guest(params, env):
    """
    Check the current memory size in the guest
    """
    params.doc_logger.info(STEPS + "# cat /proc/meminfo | grep MemTotal")
    params.doc_logger.info(RESULT + "MemTotal:        %d kB" % params.curmem)

#!/usr/bin/env python

# Copyright (C) 2021-2022, Xilinx, Inc.  All rights reserved.
# Copyright (C) 2022-2023, Advanced Micro Devices, Inc.  All rights reserved.
#
# Author:
#       Raju Kumar Pothuraju <rajukumar.pothuraju@amd.com>
#
# SPDX-License-Identifier: MIT

import os
import subprocess
import re
import sys
import shutil
import logging
logger = logging.getLogger('PetaLinux')

scripts_path = os.path.dirname(os.path.realpath(__file__))
libs_path = scripts_path + '/libs'
sys.path = sys.path + [libs_path]
import plnx_vars
import bitbake_utils
from common_utils import *


def is_hwflow_sdt(proot):
    '''Determine if the project configured with SDT or XSA'''
    hdf_ext = get_config_value('HDF_EXT',
                               plnx_vars.MetaDataFile.format(proot))
    if hdf_ext == 'dts':
        hdf_ext = 'sdt'
    return hdf_ext


def get_plnx_projects_from_bsp(source):
    '''Get the Projects from BSP tar ball'''
    contents_cmd = 'tar --exclude="*/*/*" -tzf "%s"' % (source)
    contents, stderr = runCmd(contents_cmd, os.getcwd(), shell=True)
    projects = []
    for content in contents.split():
        project_name = content.split('/')[0]
        projects.append(project_name) if project_name not in projects else ''

    real_proj = []
    for p in projects:
        if plnx_vars.MetaDataDir.format(p) in contents:
            real_proj.append(p)

    return real_proj


def exit_not_plnx_project(proot):
    '''Check the proot is valide or not by checking .petalinux directory'''
    workingdir = os.getcwd()
    parentdir = ''
    if proot:
        proot = os.path.realpath(proot)
    else:
        while True:
            if os.path.exists(plnx_vars.MetaDataDir.format(workingdir)):
                proot = workingdir
                if bool(re.search(r"\s", proot)):
                    logger.error('Your project directory %s includes space.'
                                 'PetaLinux project directory should not include space.' % (proot))
                    sys.exit(255)
                return proot
            parentdir = os.path.dirname(workingdir)
            if parentdir == workingdir:
                break
            workingdir = parentdir
        logger.error(
            'You are not inside a PetaLinux project. Please specify a PetaLinux project!')
        sys.exit(255)

    if not os.path.exists(plnx_vars.MetaDataDir.format(proot)):
        logger.error('"%s" is not a valid PetaLinux project.'
                     'Please create a project with petalinux-create -t project first!' % (proot))
        sys.exit(255)

    if bool(re.search(r"\s", proot)):
        logger.error('Your project directory %s includes space.'
                     'PetaLinux project directory should not include space.' % (proot))
        sys.exit(255)
    return proot


def petalinux_version_check(proot):
    '''PetaLinux version check'''
    CreateFile(plnx_vars.MetaDataFile.format(proot))
    proj_version = get_config_value(plnx_vars.PetaLinux_Ver_Str,
                                    plnx_vars.MetaDataFile.format(proot))
    if not proj_version:
        update_config_value(plnx_vars.PetaLinux_Ver_Str, plnx_vars.PetaLinux_Ver,
                            plnx_vars.MetaDataFile.format(proot))
    elif plnx_vars.PetaLinux_Ver != proj_version:
        logger.warning(
            'Your PetaLinux project was last modified by PetaLinux SDK version: "%s"' % (proj_version))
        logger.warning(
            'however, you are using PetaLinux SDK version: "%s"' % (
                plnx_vars.PetaLinux_Ver))
        if os.environ.get('PLNX_IGNORE_VER_CHK', ''):
            logger.warning('PLNX_IGNORE_VER_CHK is set, skip version checking')
            return True
        userchoice = input(
            'Please input "y/Y" to continue. Otherwise it will exit![n]')
        if userchoice in ['y', 'Y', 'yes', 'Yes', 'YEs', 'YES']:
            update_config_value(plnx_vars.PetaLinux_Ver_Str,
                                petalinux_ver, metadata_file)
            return True
        else:
            return False
    return True


def get_soc_variant(proot):
    '''Read SOC_VARIANT from config'''
    variant = get_config_value(plnx_vars.SOC_VariantConf,
                               plnx_vars.SysConfFile.format(proot), 'choice', '=y').lower()
    return variant


def get_system_arch(proot):
    '''Read arch from config'''
    arch = get_config_value(plnx_vars.ARCH_Conf.format(proot),
                            plnx_vars.SysConfFile.format(proot), 'choice', '=y').lower()
    return arch


def get_xilinx_arch(proot):
    '''Read xilinx_arch from config'''
    xilinx_arch = get_config_value(plnx_vars.Xilinx_Arch_Conf.format(proot),
                                   plnx_vars.SysConfFile.format(proot), 'choice', '=y').lower()
    if xilinx_arch == 'versal':
        soc_variant = get_soc_variant(proot)
        if soc_variant == 'versalnet':
            xilinx_arch = 'versal-net'
    return xilinx_arch


def get_buildtools_path(Type=''):
    '''Return buildtools path from tool'''
    if Type == 'extended':
        return os.path.join(plnx_vars.YoctoSrcPath, 'buildtools_extended',
                            'environment-setup-x86_64-petalinux-linux')
    else:
        return os.path.join(plnx_vars.YoctoSrcPath, 'buildtools',
                            'environment-setup-x86_64-petalinux-linux')


def get_yocto_path(proot, arch):
    '''Return yocto sdk path and arch'''
    if is_hwflow_sdt(proot) == 'sdt':
        arch = 'aarch64_dt'
    yocto_path = os.path.join(plnx_vars.EsdkSrcPath, arch)
    return yocto_path, arch


def get_workspace_path(proot):
    '''Return workspace path'''
    workspace_path = get_config_value(
        plnx_vars.DevtoolConf, plnx_vars.SysConfFile.format(proot))
    workspace_path = workspace_path.replace('${PROOT}', proot)
    workspace_path = workspace_path.replace('$PROOT', proot)
    return workspace_path


def config_initscripts(proot):
    '''Generate the configs for busyboxt, interfaces, wired.network'''
    '''files as per the user defined config values'''
    ip_addr = get_config_value(plnx_vars.EthConfs['Prefix'],
                               plnx_vars.SysConfFile.format(proot), 'asterisk',
                               plnx_vars.EthConfs['IPConf'])
    ip_netmask = get_config_value(plnx_vars.EthConfs['Prefix'],
                                  plnx_vars.SysConfFile.format(proot), 'asterisk',
                                  plnx_vars.EthConfs['IPNetMaskConf'])
    ip_gateway = get_config_value(plnx_vars.EthConfs['Prefix'],
                                  plnx_vars.SysConfFile.format(proot), 'asterisk',
                                  plnx_vars.EthConfs['IPGetWay'])
    ip_dynamic = get_config_value(plnx_vars.EthConfs['Prefix'],
                                  plnx_vars.SysConfFile.format(proot), 'asterisk',
                                  plnx_vars.EthConfs['Dhcp'])
    eth_manual = get_config_value(
        plnx_vars.EthManualConf, plnx_vars.SysConfFile.format(proot))
    CreateDir(os.path.dirname(plnx_vars.P_Interfaces.format(proot)))
    CopyFile(plnx_vars.T_Interfaces.format(proot),
             plnx_vars.P_Interfaces.format(proot))
    CreateDir(os.path.dirname(plnx_vars.P_SystemdWired.format(proot)))
    CopyFile(plnx_vars.T_SystemdWired.format(proot),
             plnx_vars.P_SystemdWired.format(proot))
    if ip_dynamic != 'y' and eth_manual != 'y':
        add_str_to_file(plnx_vars.P_Interfaces.format(proot),
                        plnx_vars.ActInterfaceStr.format(
            ip_addr, ip_netmask, ip_gateway))
        cidr_netmask = sum(bin(int(x)).count('1') 
                           for x in ip_netmask.split('.'))
        add_str_to_file(plnx_vars.P_SystemdWired.format(proot),
                        plnx_vars.ActWiredStr.format(
            ip_addr, cidr_netmask, ip_gateway))
    if not os.path.exists(plnx_vars.P_InetDConf.format(proot)):
        CreateDir(plnx_vars.P_BusyBoxDir.format(proot))
        CopyFile(plnx_vars.T_InetDFile.format(proot),
                 plnx_vars.P_InetDConf.format(proot))
        replace_str_fromdir(plnx_vars.P_BusyBoxDir.format(proot),
                            '#telnet', 'telnet')
        replace_str_fromdir(plnx_vars.P_BusyBoxDir.format(proot),
                            '#ftp', 'ftp')
        replace_str_fromdir(plnx_vars.P_BusyBoxDir.format(proot),
                            '-w /var/ftp/', '-w')


def gen_sysconf_dtsi_file(proot):
    '''Generate sysconf.dtsi file for SDT flow'''
    sdt_machine = get_config_value('MACHINE ',
                                   plnx_vars.SdtAutoConf.format(proot)).strip()
    bootargs = get_config_value(plnx_vars.AutoBootArgsConf,
                                plnx_vars.SysConfFile.format(proot))
    if not bootargs:
        bootargs = get_config_value(plnx_vars.BootArgsCmdLineConf,
                                    plnx_vars.SysConfFile.format(proot))
    add_str_to_file(plnx_vars.SdtSystemConfDtsi.format(proot, sdt_machine),
                    plnx_vars.SystemconfBootargs.format(bootargs))
    eth_ipname = get_config_value(
        plnx_vars.EthConfs['Prefix'], plnx_vars.SysConfFile.format(proot),
        'choice', '_SELECT=y').lower()
    eth_mac = get_config_value(
        plnx_vars.EthConfs['Prefix'], plnx_vars.SysConfFile.format(proot),
        'asterisk', plnx_vars.EthConfs['Mac']).replace(':', ' ')
    if eth_ipname != 'manual':
        add_str_to_file(plnx_vars.SdtSystemConfDtsi.format(proot, sdt_machine),
                        plnx_vars.SystemconfEth.format(
            eth_ipname, eth_mac), mode='a')
    flash_ipname = get_config_value(plnx_vars.FlashIpConf,
                                    plnx_vars.SysConfFile.format(proot))
    if flash_ipname:
        prev_part_offset = '0x0'
        prev_part_size = '0x0'
        add_str_to_file(plnx_vars.SdtSystemConfDtsi.format(proot, sdt_machine),
                        plnx_vars.SystemconfFlash.format(
            flash_ipname), mode='a')
        for num in range(0, 19):
            part_offset = add_offsets(prev_part_offset, prev_part_size)
            part_name = get_config_value('%s%s%s' % (
                plnx_vars.FlashConfs['Prefix'], num, plnx_vars.FlashConfs['Name']),
                plnx_vars.SysConfFile.format(proot))
            part_size = get_config_value('%s%s%s' % (
                plnx_vars.FlashConfs['Prefix'], num, plnx_vars.FlashConfs['Size']),
                plnx_vars.SysConfFile.format(proot))
            prev_part_offset = part_offset
            prev_part_size = part_size
            if part_name:
                add_str_to_file(plnx_vars.SdtSystemConfDtsi.format(proot, sdt_machine),
                                plnx_vars.FlashPartNode.format(
                    num, part_name, part_offset, part_size), mode='a')
            else:
                break
        add_str_to_file(plnx_vars.SdtSystemConfDtsi.format(proot, sdt_machine),
                        plnx_vars.FlashendSymbols, mode='a')


def validate_hwchecksum(proot):
    '''Validate HW file checksum and info user if mismatched with the old one'''
    hw_file = ''
    if os.path.exists(plnx_vars.HWDescDir.format(proot)):
        for _file in os.listdir(plnx_vars.HWDescDir.format(proot)):
            if _file.endswith('.xsa'):
                hw_file = os.path.join(
                    plnx_vars.HWDescDir.format(proot), _file)
                break
            if _file.endswith('.dts'):
                hw_file = os.path.join(
                    plnx_vars.HWDescDir.format(proot), _file)
                break
    if not hw_file:
        logger.error('No XSA is found in %s' %
                     plnx_vars.HWDescDir.format(proot))
        sys.exit(255)
    hw_checksum_old = get_config_value('HARDWARE_CHECKSUM',
                                       plnx_vars.MetaDataFile.format(proot))
    hw_path = get_config_value('HARDWARE_PATH',
                               plnx_vars.MetaDataFile.format(proot))
    '''Checksum of get-hw-description path stored in metadata file'''
    hw_path_checksum = ''
    if os.path.isfile(hw_path):
        hw_path_checksum = get_filehashvalue(hw_path)
    '''Checksum of project-spec/hw-description'''
    hw_checksum = ''
    if os.path.isfile(hw_file):
        hw_checksum = get_filehashvalue(hw_file)
    validate_chksum = get_config_value('VALIDATE_HW_CHKSUM',
                                       plnx_vars.MetaDataFile.format(proot))

    if hw_path_checksum and hw_checksum != hw_path_checksum and validate_chksum != '0':
        logger.info('Seems like your hardware design:%s is changed,'
                    '\nplese run "petalinux-config --get-hw-description %s" for updating'
                    % (hw_path, hw_path))
        update_config_value('VALIDATE_HW_CHKSUM', '0',
                            plnx_vars.MetaDataFile.format(proot))


def setup_plnwrapper(args, proot, config_target, gen_confargs):
    '''Setting up the PetaLinux wrapper to generate the configs'''
    validate_hwchecksum(proot)
    bitbake_utils.get_yocto_source(proot)
    if is_hwflow_sdt(proot) == 'sdt':
        bitbake_utils.get_sdt_setup(proot)
    bitbake_utils.setup_bitbake_env(proot, args.logfile)
    add_layers = False
    if args.command == 'petalinux-config' and args.component != 'rootfs':
        # Not run for petalinux-config -c rootfs
        add_layers = True
    elif args.command != 'petalinux-config':
        # Run for petalinux-!{config}
        add_layers = True

    xilinx_arch = get_xilinx_arch(proot)
    bitbake_utils.run_genmachineconf(
        proot, xilinx_arch, gen_confargs, add_layers, args.logfile)
    if add_layers:
        workspace_path = get_workspace_path(proot)
        logger.info('Generating workspace directory')
        workspace_cmd = 'devtool create-workspace "%s"' % workspace_path
        bitbake_utils.run_bitbakecmd(
            workspace_cmd, proot, logfile=args.logfile, shell=True)
        remove_str_from_file(plnx_vars.LocalConf.format(proot),
                             '^include conf\/petalinuxbsp.conf')
        add_str_to_file(plnx_vars.LocalConf.format(proot),
                        'include conf/petalinuxbsp.conf\n',
                        ignore_if_exists=True, mode='a+')
    config_initscripts(proot)

    if is_hwflow_sdt(proot) == 'sdt':
        gen_sysconf_dtsi_file(proot)

#!/usr/bin/env python3

# Copyright (C) 2021-2022, Xilinx, Inc.  All rights reserved.
# Copyright (C) 2022-2024, Advanced Micro Devices, Inc.  All rights reserved.
#
# Author:
#       Raju Kumar Pothuraju <rajukumar.pothuraju>
#
# SPDX-License-Identifier: MIT

import logging
import os
import re
import shutil
import subprocess
import sys

logger = logging.getLogger('PetaLinux')


def CreateDir(dirpath):
    '''Creates Directory'''
    if not os.path.exists(dirpath):
        try:
            os.makedirs(dirpath, exist_ok=True)
        except IOError:
            logger.error('Unable to create directory at %s' % dirpath)
            sys.exit(255)


def CreateFile(filepath):
    '''Creates a empty File'''
    if not os.path.isfile(filepath):
        with open(filepath, 'w') as f:
            pass


def RenameDir(indir, outdir):
    '''Rename the Directory'''
    if os.path.exists(indir):
        shutil.move(indir, outdir)


def RenameFile(infile, outfile):
    '''Rename File'''
    if os.path.exists(infile):
        os.rename(infile, outfile)


def RemoveDir(dirpath):
    '''Remove Directory'''
    if os.path.exists(dirpath):
        shutil.rmtree(dirpath, ignore_errors=True)


def RemoveFile(filepath):
    '''Remove file'''
    if os.path.exists(filepath):
        os.remove(filepath)


def CopyDir(indir, outdir, exclude=''):
    '''Copy Directory to Directory
    Using tar command to copy dirs which is twice
    faster than shutil.copytree and support exclude option'''
    if os.path.exists(indir):
        if not os.path.exists(outdir):
            CreateDir(outdir)
        copycmd = "tar --xattrs --xattrs-include='*' --exclude='%s' \
                -cf - -S -C %s -p . | tar --xattrs --xattrs-include='*' \
                -xf - -C %s" % (exclude, indir, outdir)
        runCmd(copycmd, os.getcwd(), shell=True)


def CopyFile(infile, dest, follow_symlinks=False):
    '''Copy File to Dir'''
    if os.path.isfile(infile):
        shutil.copy2(infile, dest, follow_symlinks=follow_symlinks)


def add_offsets(start, end):
    '''Add given offsets and return the final offset'''
    offset = hex(int(start, base=16) + int(end, base=16))
    return offset


def argreadlink(arg):
    ''' Read the realpath if path exists '''
    if os.path.exists(arg):
        arg = os.path.realpath(arg)
    return arg


def ToUpper(string):
    '''Convert string to Upper case'''
    return string.upper()


def CheckFileExists(filepath, failed_msg=''):
    '''Check if File exists or not and exit if not found'''
    if not os.path.exists(filepath):
        logger.error('%sFile "%s" doesnot exist.' % (failed_msg, filepath))
        sys.exit(255)


def GetFileType(filepath):
    cmd = 'file %s' % filepath
    stdout = runCmd(cmd, os.getcwd(), shell=True)
    return stdout[0]


def IsElfFile(filepath):
    stdout = GetFileType(filepath)
    if bool(re.search('ELF', stdout)):
        return True
    return False


def runCmd(command, out_dir, extraenv=None,
           failed_msg='', shell=False, checkcall=False):
    '''Run Shell commands from python'''
    command = command.split() if not shell else command
    logger.debug(command)
    env = os.environ.copy()
    if extraenv:
        for k in extraenv:
            env[k] = extraenv[k]
    if checkcall:
        subprocess.check_call(
            command, env=extraenv, cwd=out_dir, shell=shell)
        return
    else:
        process = subprocess.Popen(command,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE,
                                   env=env, shell=shell,
                                   executable='/bin/bash',
                                   cwd=out_dir)
        stdout, stderr = process.communicate()
        if process.returncode != 0:
            raise Exception('\n%s\n%s\n%s' %
                            (stdout.decode('utf-8'),
                             stderr.decode('utf-8'),
                             failed_msg))
        else:
            if not stdout is None:
                stdout = stdout.decode("utf-8")
            if not stderr is None:
                stderr = stderr.decode("utf-8")
        return stdout, stderr


def replace_str_fromdir(dirpath, search_str, replace_str, include_dir_names=False):
    '''Replace the string with string in the files and directory names
    Gets the all files from dirpath and search for the given search_str
    replace with replace_str if found in file and filenames
    '''
    for dname, dirs, files in os.walk(dirpath):
        for fname in files:
            fpath = os.path.join(dname, fname)
            try:
                with open(fpath) as f:
                    s = f.read()
                    s = s.replace(search_str, replace_str)
            except UnicodeDecodeError:
                pass
            if include_dir_names:
                fname = fname.replace(search_str, replace_str)
                RemoveFile(fpath)
                fpath = os.path.join(dname, fname)
            with open(fpath, 'w') as f:
                f.write(s)


def remove_str_from_file(filename, string):
    '''Remove the line that matches with string'''
    lines = []
    if os.path.exists(filename):
        with open(filename, 'r') as file_data:
            lines = file_data.readlines()
        with open(filename, 'w') as file_data:
            for line in lines:
                if re.search(string, line):
                    continue
                file_data.write(line)


def add_str_to_file(filename, string, ignore_if_exists=False, mode='w'):
    '''Add string or line into the given file and ignore if already exists in file'''
    lines = []
    string_found = False
    if os.path.exists(filename):
        with open(filename, 'r') as file_data:
            lines = file_data.readlines()
    for line in lines:
        if re.match(string, line):
            string_found = True
    if not ignore_if_exists or not string_found:
        with open(filename, mode) as file_f:
            file_f.write(string)


def concate_files(fromfile, tofile):
    '''Merge files into one'''
    with open(tofile, 'a') as tofile_f:
        with open(fromfile, 'r') as fromfile_f:
            tofile_f.write(fromfile_f.read())


def get_filehashvalue(filename):
    '''Get sha256 for given file'''
    import hashlib
    import mmap
    method = hashlib.sha256()
    with open(filename, "rb") as f:
        try:
            with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                for chunk in iter(lambda: mm.read(8192), b''):
                    method.update(chunk)
        except ValueError:
            # You can't mmap() an empty file so silence this exception
            pass
    return method.hexdigest()


def get_free_port(port=9000):
    '''Get the free port to use'''
    import socket, random
    from contextlib import closing
    while True:
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
            if sock.connect_ex(('localhost', port)) == 0:
                # Port is open, so not free
                # Generate random int and try again
                port = port + random.randint(0, 9)
                continue
            else:
                # Port is not open, so free
                # return port
                return port


def update_config_value(macro, value, filename):
    '''Update the value for macro in a given filename'''
    lines = []
    if os.path.exists(filename):
        with open(filename, 'r') as file_data:
            lines = file_data.readlines()
        file_data.close()

    with open(filename, 'w') as file_data:
        for line in lines:
            if re.search('# %s is not set' % macro, line) or re.search('%s=' % macro, line):
                continue
            file_data.write(line)
        if value == 'disable':
            file_data.write('# %s is not set\n' % macro)
        else:
            file_data.write('%s=%s\n' % (macro, value))
    file_data.close()


def get_config_value(macro, filename, Type='bool', end_macro='=y'):
    '''Get the macro value from given filename'''
    lines = []
    if os.path.exists(filename):
        with open(filename, 'r') as file_data:
            lines = file_data.readlines()
        file_data.close()
    value = ''
    if Type == 'bool':
        for line in lines:
            line = line.strip()
            if line.startswith(macro + '='):
                value = line.replace(macro + '=', '').replace('"', '')
                break
    elif Type == 'choice':
        for line in lines:
            line = line.strip()
            if line.startswith(macro) and line.endswith(end_macro):
                value = line.replace(macro, '').replace(end_macro, '')
                break
    elif Type == 'choicelist':
        for line in lines:
            line = line.strip()
            if line.startswith(macro) and line.endswith(end_macro):
                value += ' ' + line.replace(macro, '').replace(end_macro, '')
    elif Type == 'asterisk':
        for line in lines:
            line = line.strip()
            if line.startswith(macro) and re.search(end_macro, line):
                value = line.split('=')[1].replace('"', '')
                break
    return value


def check_gcc_version():
    ''' Check GCC version of the Host machine v/s required version'''
    gcc_cmd = 'gcc --version | sed -ne "s/.* \([0-9]\+\.[0-9]\+\)\.[0-9]\+.*/\\1/p"'
    cur_version = runCmd(gcc_cmd, os.getcwd(), shell=True)
    required_version = 7
    if float(cur_version[0].strip()) <= required_version:
        logger.error('Seems like Host machine does not have gcc %s or greater version.'
                     % required_version)
        sys.exit(255)
    return cur_version


def get_filesystem_id(path):
    '''Run stat command and get the filesystem ID'''
    try:
        return subprocess.check_output(["stat", "-f", "-c", "%t", path]).decode('utf-8').strip()
    except subprocess.CalledProcessError:
        return None


def check_tool(tools=[], failed_msg=''):
    '''Check the tools exists in PATH variable or not and give error if not found'''
    for tool in tools.split():
        tool = tool.lower()
        tool_path = shutil.which(tool)
        if not tool_path:
            logger.error(
                'This tool requires "%s" and it is missing. %s' % (tool, failed_msg))
            sys.exit(255)


def add_dictkey(Dict, key, sub_key, value, append=False, sep=', '):
    '''Add Elements to the given Dictionary'''
    if sub_key:
        if not append:
            try:
                Dict[key][sub_key] = value
            except KeyError:
                Dict[key] = {}
                Dict[key][sub_key] = value
        else:
            try:
                Dict[key][sub_key] += sep + value
            except KeyError:
                Dict[key][sub_key] = ''
                Dict[key][sub_key] += value
    else:
        Dict[key] = value

def GetFileSize(FilePath):
    if os.path.isfile(FilePath):
        FileInfo = os.stat(FilePath)
        return FileInfo.st_size

def HighestPowerof2(FilePath):
    FileSize=GetFileSize(FilePath)
    if isinstance(FileSize, float):
        Size_=int(FileSize) + 1
    else:
        Size_=FileSize

    if not Size_ & (Size_ - 1) == 0 and Size_ > 0:
        import math
        p = int(math.log(Size_, 2)) + 1
        return int(pow(2, p))
    else:
        return Size_

def MakePowerof2(Image):
    Power2Size = HighestPowerof2(Image)
    QemuImgCmd = 'qemu-img resize -f raw %s %s' % (Image, Power2Size)
    stdout = runCmd(QemuImgCmd, os.getcwd(),
                               failed_msg='Fail to launch qemu img cmd', shell=True, checkcall=True)

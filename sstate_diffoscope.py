#!/usr/bin/env python3

import os
import sys
import argparse
import subprocess

class SstateType(object):
    TARGET = 1
    NATIVE = 2
    NATIVESDK = 3 

class Sstate(object):
    def __init__(self, name, full_arch, version, small_arch, signature,
            task):
        self.name = name
        self.full_arch = full_arch
        self.version = version
        self.small_arch = small_arch
        self.signature = signature
        self.task = task

        if self.name.startswith('nativesdk-'):
            self.type = SstateType.NATIVESDK
        elif self.name.endswith('-native'):
            self.type = SstateType.NATIVE
        else:
            self.type = SstateType.TARGET

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False

        if self.name == other.name and self.full_arch == other.full_arch and \
                self.version == other.version and self.type == other.type and \
                self.signature == other.signature and self.task == other.task:
            return True

        return False

    def __hash__(self):
        return hash((self.name, self.full_arch, self.version, self.type,
            self.signature, self.task))

# sstate:netbase:i586-poky-linux:5.4:r0:i586:3:0f4041f61f57f7abd8523bf2816e_populate_sysroot.tgz
def build_sstate(filename):
    info = filename.split(':')

    name = info[1]
    full_arch = info[2]
    version = "%s-%s" % (info[3], info[4])
    small_arch = info[5]

    extra_info = info[7].strip('tgz')[0:-1].split('_')
    signature = extra_info[0]
    task = "_".join(extra_info[1:])

    return Sstate(name, full_arch, version, small_arch, signature, task)

def get_sstates(directory):
    sstates = {}

    for root, dirs, files in os.walk(directory):
        for f in files:
            full_f = os.path.join(root, f)

            if f.endswith('.tgz'):
                sstate = build_sstate(f)
                sstates[sstate] = full_f

    return sstates

DEFAULT_OUTPUT_DIR = 'sstate_diff_results'
def main():
    parser = argparse.ArgumentParser(
            description="Shared states binary diff tool",
            add_help=False)
    parser.add_argument('sstate_dir', metavar='SSTATE_DIR', nargs='+',
            help='Shared states directories to make binary diff')
    parser.add_argument('-o', '--output-dir',
            help='Output directory: %s' % DEFAULT_OUTPUT_DIR,
            action='store', default=DEFAULT_OUTPUT_DIR)

    parser.add_argument('-h', '--help', action='help',
            default=argparse.SUPPRESS,
            help='show this help message and exit')

    args = parser.parse_args()

    if len(args.sstate_dir) != 2:
        print("Please specify only two shared state directories.")
        sys.exit(1)

    try:
        subprocess.check_output("diffoscope --version", shell=True)
    except subprocess.SubprocessError:
        print("Please install diffoscope")
        sys.exit(1)
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)

    sstates1 = get_sstates(args.sstate_dir[0])
    sstates2 = get_sstates(args.sstate_dir[1])

    def execute_diffoscope(s):
        binary_equal = True
        if s.type == SstateType.TARGET and s.task == 'populate_sysroot':
            if s in sstates2:
                print('IN %s -> %s' % (sstates1[s], sstates2[s]))

                sdir = os.path.join(args.output_dir, s.name)
                try:
                    subprocess.check_output('diffoscope --html-dir %s %s %s' %\
                            (sdir, sstates1[s], sstates2[s]), shell=True)
                except subprocess.CalledProcessError:
                    binary_equal = False
            else:
                print('NOT IN: %s' % (sstates1[s]))

        return binary_equal

    for s in sstates1:
        execute_diffoscope(s)

if __name__ == '__main__':
    try:
        ret =  main()
    except Exception:
        ret = 1
        import traceback
        traceback.print_exc()
    sys.exit(ret)


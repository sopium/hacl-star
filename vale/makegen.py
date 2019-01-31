# This file requires Python version >= 3.6

import argparse
import re
import sys
import os, os.path
import subprocess
import platform
import fnmatch
import pathlib
import shutil
import glob

if sys.version_info < (3, 6):
  print(f'Requires Python version >= 3.6, found version {sys.version_info}')  # If the syntax of this line is invalid, the version of Python is probably older than 3.6
  exit(1)

##################################################################################################
#
#   Command-line options
#
##################################################################################################

if 'VALE_HOME' in os.environ:
  vale_default_path = os.environ['VALE_HOME']
else:
  vale_default_path = '../../vale'

if 'KREMLIN_HOME' in os.environ:
  kremlin_default_path = os.environ['KREMLIN_HOME']
else:
  kremlin_default_path = '../../kremlin'

if 'FSTAR_HOME' in os.environ:
  fstar_default_path = os.environ['FSTAR_HOME']
else:
  fstar_default_path = '../../FStar'

arg_parser = argparse.ArgumentParser()

def AddOption(name, dest, type, default, action, help):
  arg_parser.add_argument(name, dest = dest, type = type, default = default, action = action, help = help)

def AddOptYesNo(name, dest, default, help):
  arg_parser.add_argument('--' + name, dest = dest, default = default, action = 'store_true', help = f'{help} (default {default})')
  arg_parser.add_argument('--NO-' + name, dest = dest, default = default, action = 'store_false')

# Retrieve tool-specific command overrides passed in by the user
AddOption('--OUT-MAKE', dest = "out_make", type = str, default = None, action = 'store',
  help = 'Generate makefile using specified path')
AddOption('--OUT-SCONS', dest = "out_scons", type = str, default = None, action = 'store',
  help = 'Generate SConscript file using specified path')
AddOption('--VALE-PATH', dest = 'vale_path', type = str, default = vale_default_path, action = 'store',
  help = 'Specify the path to Vale tool')
AddOption('--KREMLIN-PATH', dest = 'kremlin_path', type = str, default = kremlin_default_path, action = 'store',
  help = 'Specify the path to kreMLin')
AddOption('--FSTAR-PATH', dest = 'fstar_path', type = str, default = fstar_default_path, action = 'store',
  help = 'Specify the path to F* tool')
AddOption('--FSTAR-Z3', dest = 'fstar_z3', type = str, default = '', action = 'store',
  help = 'Specify the path to z3 or z3.exe for F*')
AddOptYesNo('FSTAR-MY-VERSION', dest = 'fstar_my_version', default = False,
  help = 'Use version of F* that does not necessarily match .tested_fstar_version')
AddOptYesNo('Z3-MY-VERSION', dest = 'z3_my_version', default = False,
  help = 'Use version of Z3 that does not necessarily match .tested_z3_version')
AddOptYesNo('VALE-MY-VERSION', dest = 'vale_my_version', default = False,
  help = 'Use version of Vale that does not necessarily match .vale_version')
AddOptYesNo('RECORD-HINTS', dest = 'record_hints', default = False,
  help = 'Record new F* .hints files into the hints directory')
AddOptYesNo('USE-HINTS', dest = 'use_hints', default = True,
  help = 'Use F* .hints files from the hints directory')
AddOption('--FARGS', dest = 'fstar_user_args', type = str, default = [], action = 'append',
  help = 'Supply temporary additional arguments to the F* compiler')
AddOption('--VARGS', dest = 'vale_user_args', type = str, default = [], action = 'append',
  help = 'Supply temporary additional arguments to the Vale compiler')
AddOption('--KARGS', dest = 'kremlin_user_args', type = str, default = [], action = 'append',
  help = 'Supply temporary additional arguments to the Kremlin compiler')
AddOption('--CARGS', dest = 'c_user_args', type = str, default = "", action = 'append',
  help = 'Supply temporary additional arguments to the C compiler')
AddOption('--OPENSSL', dest = 'openssl_path', type = str, default = None, action = 'store',
  help = 'Specify the path to the root of an OpenSSL source tree')
AddOption('--CACHE-DIR', dest = 'cache_dir', type = str, default = None, action = 'store',
  help = 'Specify the SCons Shared Cache Directory')
AddOptYesNo('VERIFY', dest = 'verify', default = True,
  help = 'Verify and compile, or compile only')
AddOption('--ONE', dest = 'single_vaf', type = str, default = None, action = 'store',
  help = 'Only verify one specified .vaf file, and in that file, only verify procedures or verbatim blocks marked as {:verify}.')
AddOptYesNo('COLOR', dest = 'do_color', default = True,
  help="Add color to build output")
AddOptYesNo('DUMP-ARGS', dest = 'dump_args', default = False,
  help = "Print arguments that will be passed to the verification tools")
AddOptYesNo('FSTAR-EXTRACT', dest = 'fstar_extract', default = False,
  help = "Generate .S and .asm files via F* extraction to OCaml")
AddOptYesNo('MIN-TEST', dest = 'min_test', default = False,
  help = "Only run on a minimal set of test files")
AddOptYesNo('PROFILE', dest = 'profile', default = False,
  help = "Turn on profile options to measure verification performance (note: --NO-USE-HINTS is recommended when profiling)")

args = arg_parser.parse_args()
out_make = args.out_make
out_scons = args.out_scons
vale_path = os.path.abspath(args.vale_path)
kremlin_path = os.path.abspath(args.kremlin_path)
fstar_path = os.path.abspath(args.fstar_path)
fstar_user_args = args.fstar_user_args
vale_user_args = args.vale_user_args
kremlin_user_args = args.kremlin_user_args
c_user_args = args.c_user_args
openssl_path = args.openssl_path
fstar_my_version = args.fstar_my_version
z3_my_version = args.z3_my_version
vale_my_version = args.vale_my_version
fstar_extract = args.fstar_extract
record_hints = args.record_hints
use_hints = args.use_hints
do_color = args.do_color
dump_args = args.dump_args
single_vaf = args.single_vaf
is_single_vaf = not (single_vaf is None)
min_test = args.min_test
profile = args.profile
verify = args.verify
fstar_z3 = args.fstar_z3

##################################################################################################
#
#   Environment settings
#
##################################################################################################

target_arch = 'x86'
if (sys.platform == 'win32' and (os.getenv('PLATFORM') == 'X64' or platform.machine() == 'AMD64')) or platform.machine() == 'x86_64':
  target_arch = 'amd64'

CCPDBFLAGS = []
CCFLAGS = [c_user_args]
LINKFLAGS = []
CXXFLAGS = []
AS = ''
mono = ''
if sys.platform == 'win32' and not ('SHELL' in os.environ):
  import importlib.util
  CCPDBFLAGS.extend(['/Zi /Fd${TARGET.base}.pdb'])
  # Use kremlib.h without primitive support for uint128_t.
  CCFLAGS.extend(['/Ox', '/Gz', '/DKRML_NOUINT128'])
  LINKFLAGS.extend(['/DEBUG'])
  if os.getenv('PLATFORM') == 'X64':
    AS = 'ml64'
else:
  CCFLAGS.extend(['-O3', '-flto', '-g', '-DKRML_NOUINT128'])
  CXXFLAGS.extend(['-std=c++11'])  # This option is C++ specific
  if sys.platform != 'win32':
    mono = 'mono'

# Helper class to specify per-file command-line options for verification.
class BuildOptions:
  # First argument is mandatory (verification options); all others are optional named arguments
  def __init__(self, args, vale_includes = None):
    self.verifier_flags = args
    self.vale_includes = vale_includes

##################################################################################################
#
#   Utilities
#
##################################################################################################

all_targets = set()
cmd_targets = {}

def Flatten(x):
  return [z for y in x for z in Flatten(y)] if isinstance(x, list) else [x]

def File(path):
  return os.path.normpath(os.path.relpath(path)).replace('\\', '/')

def Dir(path):
  return os.path.normpath(os.path.relpath(path)).replace('\\', '/')

def FindFile(name, paths):
  for p in paths:
    f = os.path.join(p, name)
    if os.path.exists(f):
      return File(f)
  return None

def CopyFile(target, source):
  all_targets.add(target)
  if target in cmd_targets:
    if source != cmd_targets[target]:
      raise Exception(f'incompatible commands for target {target}')
    return target
  cmd_targets[target] = source
  if out_make != None:
    make_file.write(f'{target} : {source}\n')
    make_file.write(f'\tcp {source} {target}\n\n')
  if out_scons != None:
    scons_file.write(f'  env.Command({target}, {source}, Copy({target}, {source}))\n')
  return target

def Depends(targets, sources):
  targets = Flatten(targets)
  sources = Flatten(sources)
  for t in targets:
    all_targets.add(t)
  if targets != []:
    if out_make != None:
      make_file.write(f'{" ".join(targets)} : {" ".join(sources)}\n\n')
    if out_scons != None:
      scons_file.write(f'  env.Depends({targets}, {sources})\n')

def Command(targets, sources, cmd):
  targets = Flatten(targets)
  sources = Flatten(sources)
  for t in targets:
    all_targets.add(t)
    if t in cmd_targets:
      if cmd != cmd_targets[t]:
        raise Exception(f'incompatible commands for target {t}')
      return t
    cmd_targets[t] = cmd
  if out_make != None:
    make_file.write(f'{targets[0]} : {" ".join(sources)}\n')
    make_file.write(f'\t{cmd}\n')
    # ugh, this is how we declare multiple outputs:
    for t in targets[1:]:
      make_file.write(f'{t} : {targets[0]}\n')
    make_file.write(f'\n')
  if out_scons != None:
    scons_file.write(f'  env.Command({targets}, {sources},\n')
    scons_file.write(f'    {repr(cmd)})\n')
  return targets

def Assemble(target, source):
  all_targets.add(target)
  if out_make != None:
    make_file.write(f'{target} : {" ".join(source)}\n')
    make_file.write(f'\t$(CC) -c -o {target} {" ".join(source)}\n\n')
  if out_scons != None:
    scons_file.write(f'  env.Object({repr(target)}, {repr(source)})\n')
  return target

def CcCpp(cc, target, source):
  all_targets.add(target)
  if out_make != None:
    make_file.write(f'{target} : {" ".join(source)}\n')
    make_file.write(f'\t{cc} {" ".join(CCFLAGS)} -o {target} {" ".join(source)}\n\n')
  if out_scons != None:
    scons_file.write(f'  env.Program({repr(target)}, {repr(source)})\n')
  return target

def Cc(target, source):
  CcCpp(f'$(CC)', target, source)

def Cpp(target, source):
  #CcCpp('$(CXX)', target, source)
  CcCpp(f'$(subst gcc,g++,$(CC)) {" ".join(CXXFLAGS)}', target, source)

##################################################################################################
#
#   Configuration settings
#
##################################################################################################

def fstar_default_args_nosmtencoding(relative=True):
  cache_dir = 'obj/cache_checked'
  cache_dir = cache_dir if relative else os.path.abspath(cache_dir)

  return ('--max_fuel 1 --max_ifuel 1'
    + (' --initial_ifuel 1' if is_single_vaf else ' --initial_ifuel 0')
    # The main purpose of --z3cliopt smt.QI.EAGER_THRESHOLD=100 is to make sure that matching loops get caught
    # Don't remove unless you're sure you've used the axiom profiler to make sure you have no matching loops
    + ' --z3cliopt smt.arith.nl=false --z3cliopt smt.QI.EAGER_THRESHOLD=100 --z3cliopt smt.CASE_SPLIT=3'
    + ' --hint_info'
    + (' --use_hints --use_hint_hashes' if use_hints else '')
    + (' --cache_off' if record_hints else ' --cache_checked_modules')
    + ' --cache_dir ' + cache_dir
    + ' --use_extracted_interfaces true'
    )

def fstar_default_args(relative=True):
  return (fstar_default_args_nosmtencoding(relative)
  + ' --smtencoding.elim_box true --smtencoding.l_arith_repr native --smtencoding.nl_arith_repr wrapped'
  )

fstar_record_hints = ' --record_hints' if record_hints else ''

vale_scons_args = '-disableVerify -omitUnverified' if is_single_vaf else ''
vale_includes = f'-include {File("code/lib/util/operator.vaf")}'

verify_paths = [
  'code',
  'specs',
]

class ExternalFile:
  def __init__ (self, filename):
    self.filename = filename

  def obj_name(self):
    return 'obj/external/' + os.path.basename(self.filename)

external_files = [
  ExternalFile(f'{fstar_path}/examples/tactics/CanonCommSwaps.fst'),
  ExternalFile(f'{fstar_path}/examples/tactics/CanonCommMonoid.fst'),
  ExternalFile(f'{fstar_path}/examples/tactics/CanonCommSemiring.fst'),
  ExternalFile(f'{kremlin_path}/kremlib/C.Loops.fst'),
  ExternalFile(f'{kremlin_path}/kremlib/Spec.Loops.fst'),
  ExternalFile(f'{kremlin_path}/kremlib/FStar.Kremlin.Endianness.fst'),
  ExternalFile('../specs/Spec.Hash.PadFinish.fst'),
  ExternalFile('../specs/Spec.Hash.Lemmas0.fst'),
  ExternalFile('../specs/Spec.Hash.Lemmas.fst'),
  ExternalFile('../specs/derived/Spec.Hash.Incremental.fst'),
  ExternalFile('../specs/Spec.SHA2.fst'),
  ExternalFile('../specs/Spec.SHA2.fsti'),
  ExternalFile('../specs/Spec.SHA2.Constants.fst'),
  ExternalFile('../specs/Spec.SHA1.fsti'),
  ExternalFile('../specs/Spec.SHA1.fst'),
  ExternalFile('../specs/Spec.MD5.fst'),
  ExternalFile('../specs/Spec.MD5.fsti'),
  ExternalFile('../specs/Spec.Hash.fst'),
  ExternalFile('../specs/Spec.Hash.Definitions.fst'),
]

no_extraction_files = [File(x) for x in [
  'obj/ml_out/CanonCommMonoid.ml',
  'obj/ml_out/CanonCommSemiring.ml',
  'obj/ml_out/X64_Poly1305_Math.ml',
  'obj/ml_out/Vale_Tactics.ml',
  'obj/ml_out/FastHybrid_helpers.ml',
  'obj/ml_out/FastMul_helpers.ml',
  'obj/ml_out/FastSqr_helpers.ml',
  'obj/ml_out/FastUtil_helpers.ml',
]]

#
# Table of files we exclude from the minimal test suite
# (typically for performance reasons)
# Note that the entries below are prefixes of blacklisted files
#
min_test_suite_blacklist = [File(x) for x in [
  'obj/code/crypto/aes/x64/X64.GCMencrypt.fst',
  'obj/code/crypto/aes/x64/X64.GCMdecrypt.fst',
  'obj/code/thirdPartyPorts/OpenSSL/poly1305/x64/X64.Poly1305.fst',
  'obj/code/crypto/aes/x64/X64.GHash',
  'obj/code/crypto/aes/x64/X64.GCTR.fst',
  'obj/code/crypto/aes/x64/X64.AES.fst',
  'obj/code/thirdPartyPorts/Intel/aes/x64/X64.AESCTR',
]]

manual_dependencies = {
}

#
# Table of special-case sources which requires non-default arguments
#
verify_options = [
  ('code/lib/util/operator.vaf', BuildOptions(fstar_default_args(), vale_includes = '')),

  # Special treatment for sensitive modules

  # Disable verification by adding 'filename': None

#  ('code/thirdPartyPorts/rfc7748/curve25519/x64/X64.FastSqr.vaf', None),

  ('code/arch/x64/interop/*', BuildOptions(fstar_default_args_nosmtencoding().replace('--z3cliopt smt.arith.nl=false', '').replace('--z3cliopt smt.QI.EAGER_THRESHOLD=100', ''))),

  #'src/thirdPartyPorts/OpenSSL/poly1305/x64/X64.Poly1305.vaf': None,

  ('code/*/*.fst', BuildOptions(fstar_default_args())),
  ('code/*/*.fsti', BuildOptions(fstar_default_args())),
  ('specs/*/*.fst', BuildOptions(fstar_default_args())),
  ('specs/*/*.fsti', BuildOptions(fstar_default_args())),

  # .fst/.fsti files default to this set of options
  ('.fst', BuildOptions(fstar_default_args() + ' --use_two_phase_tc false')),
  ('.fsti', BuildOptions(fstar_default_args() + ' --use_two_phase_tc false')),

  ('code/arch/x64/Views.fst', BuildOptions(fstar_default_args().replace('--smtencoding.nl_arith_repr wrapped', '--smtencoding.nl_arith_repr native'))),
  ('code/arch/x64/X64.Bytes_Semantics.fst', BuildOptions(fstar_default_args().replace('--smtencoding.nl_arith_repr wrapped', '--smtencoding.nl_arith_repr native'))),

  ('code/arch/x64/X64.BufferViewStore.fst', BuildOptions(fstar_default_args_nosmtencoding() + ' --smtencoding.elim_box true')),
  ('code/lib/collections/Collections.Lists.fst', BuildOptions(fstar_default_args().replace('--z3cliopt smt.QI.EAGER_THRESHOLD=100',''))),
  ('code/crypto/poly1305/x64/X64.Poly1305.Util.fst', BuildOptions(fstar_default_args_nosmtencoding())),
  ('code/crypto/poly1305/x64/X64.Poly1305.Util.fsti', BuildOptions(fstar_default_args_nosmtencoding())),
  ('code/arch/x64/X64.Memory.fst', BuildOptions(fstar_default_args_nosmtencoding().replace('--use_extracted_interfaces true', '').replace('--z3cliopt smt.arith.nl=false', '') + '--smtencoding.elim_box true ')),
  ('code/arch/x64/X64.Memory_Sems.fst', BuildOptions(fstar_default_args_nosmtencoding().replace('--use_extracted_interfaces true', '').replace('--z3cliopt smt.arith.nl=false', '') + '--smtencoding.elim_box true ')),
  ('code/arch/x64/Interop.fst', BuildOptions(fstar_default_args_nosmtencoding().replace('--use_extracted_interfaces true', '').replace('--z3cliopt smt.QI.EAGER_THRESHOLD=100', '') + '--smtencoding.elim_box true ')),
  ('code/lib/util/BufferViewHelpers.fst' , BuildOptions(fstar_default_args_nosmtencoding().replace('--z3cliopt smt.arith.nl=false', ''))),

  # We copy these files from F*'s library because we need to generate a .checked file for them,
  # but we don't need to reverify them:
  ('obj/external/*.fst', BuildOptions('--cache_checked_modules --admit_smt_queries true')),

  # .vaf files default to this set of options when compiling .fst/.fsti
  ('.vaf', BuildOptions(fstar_default_args() + ' --use_two_phase_tc false'))
]

verify_options_dict = { k:v for (k,v) in verify_options}

# --NOVERIFY is intended for CI scenarios, where the Win32/x86 build is verified, so
# the other build flavors do not redundently re-verify the same results.
fstar_no_verify = ''
if not verify:
  print('***\n*** WARNING:  NOT VERIFYING ANY CODE\n***')
  fstar_no_verify = '--admit_smt_queries true'

# Find Z3 for F*
found_z3 = False
if fstar_z3 == '':
  fstar_z3 = File('tools/Z3/z3.exe') if sys.platform == 'win32' else 'tools/Z3/z3'
  if os.path.isfile(fstar_z3):
    found_z3 = True
  else:
    if sys.platform == 'win32':
      find_z3 = FindFile('z3.exe', os.environ['PATH'].split(';'))
    else:
      find_z3 = FindFile('z3', os.environ['PATH'].split(':'))
    if find_z3 != None:
      found_z3 = True
      fstar_z3 = str(find_z3)
else:
  found_z3 = True
fstar_z3_path = '--smt ' + (os.path.abspath(fstar_z3) if dump_args else fstar_z3)

vale_exe = File(f'{vale_path}/bin/vale.exe')
import_fstar_types_exe = File(f'{vale_path}/bin/importFStarTypes.exe')
fstar_exe = File(f'{fstar_path}/bin/fstar.exe')

##################################################################################################
#
#   Global variables
#
##################################################################################################

all_modules = []  # string names of modules
src_include_paths = []  # string paths in sources where .fst, .fsti are found
obj_include_paths = []  # string paths in obj/, but omitting the 'obj/' prefix
ml_out_deps = {}
fsti_map = {}  # map module names to .fsti File nodes (or .fst File nodes if no .fsti exists)
dump_deps = {}  # map F* type .dump file names x.dump to sets of .dump file names that x.dump depends on
vaf_dump_deps = {} # map .vaf file names x.vaf to sets of .dump file names that x.vaf depends on
vaf_vaf_deps = {} # map .vaf file names x.vaf to sets of y.vaf file names that x.vaf depends on

# match 'include {:attr1} ... {:attrn} "filename"'
# where attr may be 'verbatim' or 'from BASE'
vale_include_re = re.compile(r'include((?:\s*\{\:(?:\w|[ ])*\})*)\s*"(\S+)"', re.M)
vale_fstar_re = re.compile(r'\{\:\s*fstar\s*\}')
vale_from_base_re = re.compile(r'\{\:\s*from\s*BASE\s*\}')
vale_open_re = re.compile(r'open\s+([a-zA-Z0-9_.]+)')
vale_friend_re = re.compile(r'friend\s+([a-zA-Z0-9_.]+)')
vale_import_re = re.compile(r'module\s+[a-zA-Z0-9_]+\s*[=]\s*([a-zA-Z0-9_.]+)')

if (not sys.stdout.isatty()) or not do_color:
  # No color if the output is not a terminal or user opts out
  yellow = ''
  red = ''
  uncolor = ''
else:
  yellow = '\033[93m'
  red = '\033[91;40;38;5;217m'
  uncolor = '\033[0m'

##################################################################################################
#
#   Utility functions
#
##################################################################################################

def print_error(s):
  print(f'{red}{s}{uncolor}')

def print_error_exit(s):
  print_error(s)
  Exit(1)

# Given a File node for dir/dir/.../m.extension, return m
def file_module_name(file):
  name = os.path.basename(file)
  name = name[:1].upper() + name[1:] # capitalize first letter, as expected for F* module names
  return os.path.splitext(name)[0]

# Return '.vaf', '.fst', etc.
def file_extension(file):
  return os.path.splitext(file)[1]

# Drop the '.vaf', '.fst', etc.
def file_drop_extension(file):
  return os.path.splitext(file)[0]

# Given source File node, return File node in object directory
def to_obj_dir(file):
  if str(file).startswith('obj'):
    return file
  else:
    return File(f'obj/{file}')

def to_hint_file(file):
  return File(f'hints/{os.path.basename(file)}.hints')

def ml_out_file(sourcefile, suffix):
  module_name = file_module_name(sourcefile).replace('.', '_')
  return File(f'obj/ml_out/{module_name}{suffix}')

# Is the file from our own sources, rather than an external file (e.g., like an F* library file)?
def is_our_file(file):
  path = file
  return True in [path.startswith(str(Dir(p))) for p in ['obj'] + verify_paths]

def compute_include_paths(src_include_paths, obj_include_paths, obj_prefix):
  return src_include_paths + [str(Dir('obj/external'))] + [str(Dir(f'{obj_prefix}/{x}')) for x in obj_include_paths]

def compute_includes(src_include_paths, obj_include_paths, obj_prefix, relative=True):
  fstar_include_paths = compute_include_paths(src_include_paths, obj_include_paths, obj_prefix)
  return " ".join(["--include " + (x if relative else os.path.abspath(x)) for x in fstar_include_paths])

##################################################################################################
#
#   Configuration and environment functions
#
##################################################################################################

# Helper to look up a BuildOptions matching a srcpath File node, from the
# verify_options[] list, falling back on a default if no specific override is present.
def get_build_options(srcnode):
  srcpath = srcnode
  srcpath = srcpath.replace('\\', '/')  # switch to posix path separators
  if srcpath in verify_options_dict:    # Exact match
    return verify_options_dict[srcpath]
  else:
    for key, options in verify_options: # Fuzzy match
      if fnmatch.fnmatch (srcpath, key):
        return options
    ext = os.path.splitext(srcpath)[1]
    if ext in verify_options_dict:      # Exact extension match
      return verify_options_dict[ext]
    else:
      return None

def on_black_list(file, list):
  return True in [str(file).startswith(str(entry)) for entry in list]

def check_fstar_version():
  import subprocess
  fstar_version_file = ".tested_fstar_version"
  if os.path.isfile(fstar_version_file):
    with open(fstar_version_file, 'r') as myfile:
      lines = myfile.read().splitlines()
    version = lines[0]
    cmd = [str(fstar_exe), '--version']
    o = subprocess.check_output(cmd, stderr = subprocess.STDOUT).decode('ascii')
    lines = o.splitlines()
    for line in lines:
      if '=' in line:
        key, v = line.split('=', 1)
        if key == 'commit' and v == version:
          return
    print_error(f'Expected F* version commit={version}, but fstar --version returned the following:')
    for line in lines:
      print_error('  ' + line)
    print_error_exit(
      f'Get F* version {version} from https://github.com/FStarLang/FStar,' +
      f' modify .tested_fstar_version, or use the --FSTAR-MY-VERSION option to override.' +
      f' (We try to update the F* version frequently; feel free to change .tested_fstar_version' +
      f' to a more recent F* version as long as the build still succeeds with the new version.' +
      f' We try to maintain the invariant that the build succeeds with the F* version in .tested_fstar_version.)' +
      f' See ./INSTALL.md for more information.')

def check_z3_version(fstar_z3):
  import subprocess
  z3_version_file = ".tested_z3_version"
  if os.path.isfile(z3_version_file):
    with open(z3_version_file, 'r') as myfile:
      lines = myfile.read().splitlines()
    version = lines[0]
    cmd = [fstar_z3, '--version']
    o = subprocess.check_output(cmd, stderr = subprocess.STDOUT).decode('ascii')
    lines = o.splitlines()
    line = lines[0]
    for word in line.split(' '):
      if '.' in word:
        if word == version:
          return
        break
    print_error(f'Expected Z3 version {version}, but z3 --version returned the following:')
    for line in lines:
      print_error('  ' + line)
    print_error_exit(
      f'Get a recent Z3 executable from https://github.com/FStarLang/binaries/tree/master/z3-tested,' +
      f' modify .tested_z3_version, or use the --Z3-MY-VERSION option to override.' +
      f' (We rarely change the Z3 version; we strongly recommend using the expected version of Z3.)' +
      f' See ./INSTALL.md for more information.')

def check_vale_version():
  with open(".vale_version") as f:
    version = f.read().splitlines()[0]
  vale_version_file = f'{vale_path}/bin/.vale_version'
  vale_version = '0.2.7 or older'
  if os.path.isfile(vale_version_file):
    with open(vale_version_file) as f:
      vale_version = f.read().splitlines()[0]
  if vale_version != version:
    print_error(f'Expected Vale version {version}, but found Vale version {vale_version}')
    print_error_exit(
      f'Get version {version} from https://github.com/project-everest/vale/releases/download/v{version}/vale-release-{version}.zip,' +
      f' modify .vale_version, or use the --VALE-MY-VERSION option to override.' +
      f' See ./INSTALL.md for more information.')

def print_dump_args():
  #print('Currently using the following F* args:')
  options = fstar_default_args(relative=False)
  if len(COMMAND_LINE_TARGETS) > 0:
    options = get_build_options(File(COMMAND_LINE_TARGETS[0])).verifier_flags
    #print("The options are: %s" % options.verifier_flags)
  fstar_includes = compute_includes(src_include_paths, obj_include_paths, 'obj', relative=False)
  for option in [fstar_z3_path, fstar_no_verify, fstar_includes, fstar_user_args, options]:
    if len(option) > 0:
      print(f'{option} ', end='')
  print()
  Exit(1)

# extract a string filename out of a build failure
def bf_to_filename(bf):
  import SCons.Errors
  if bf is None: # unknown targets product None in list
    return '(unknown tgt)'
  elif isinstance(bf, SCons.Errors.StopError):
    return str(bf)
  elif bf.node:
    return str(bf.node)
  elif bf.filename:
    return bf.filename
  return '(unknown failure)'

def report_verification_failures():
  import time
  from SCons.Script import GetBuildFailures
  bf = GetBuildFailures()
  if bf:
    # bf is normally a list of build failures; if an element is None,
    # it's because of a target that scons doesn't know anything about.
    for x in bf:
      if x is not None:
        filename = bf_to_filename(x)
        if filename.endswith('.tmp') and os.path.isfile(filename):
          error_filename = filename[:-len('.tmp')] + '.error'
          stderr_filename = filename[:-len('.tmp')] + '.stderr'
          if os.path.isfile(error_filename):
            os.remove(error_filename)
          report_filename = stderr_filename if os.path.isfile(stderr_filename) else filename
          print()
          print(f'##### {red}Verification error{uncolor}')
          print('Printing contents of ' + report_filename + ' #####')
          with open(report_filename, 'r') as myfile:
            lines = myfile.read().splitlines()
            valeErrors = [line for line in lines if ("*****" in line)]
            for line in lines:
              if 'error was reported' in line or '(Error)' in line or ' failed' in line:
                line = f'{red}{line}{uncolor}'
              print(line)
          print()
          time.sleep(1)
          os.rename(filename, error_filename)
        if filename.endswith('.dump') and os.path.isfile(filename):
          stderr_filename = filename[:-len('.dump')] + '.stderr'
          report_filename = stderr_filename if os.path.isfile(stderr_filename) else filename
          print()
          print(f'##### {red}Verification error{uncolor}')
          print('Printing contents of ' + report_filename + ' #####')
          with open(report_filename, 'r') as myfile:
            lines = myfile.read().splitlines()
            valeErrors = [line for line in lines if ("*****" in line)]
            for line in lines:
              if 'error was reported' in line or '(Error)' in line or ' failed' in line:
                line = f'{red}{line}{uncolor}'
              print(line)
          print()
          time.sleep(1)
         

##################################################################################################
#
#   File and module processing functions
#
##################################################################################################

def add_module_for_file(file):
  global all_modules
  m = file_module_name(file)
  if m in all_modules:
    print(f'error: found more than one instance of module {m} (all module names must be unique for include paths to work correctly)')
    Exit(1)
  all_modules.append(m)

def add_include_dir_for_file(include_paths, file):
  d = os.path.dirname(file)
  if not (d in include_paths):
    include_paths.append(d)
    pathlib.Path(os.path.dirname(to_obj_dir(file))).mkdir(parents = True, exist_ok = True)

def include_fstar_file(file):
  options = get_build_options(file)
  add_include_dir_for_file(src_include_paths, file)
  if options != None:
    if (file_extension(file) == ".fst"):
      add_module_for_file(file)
    fsti_map[file_module_name(file)] = file

def include_vale_file(file):
  options = get_build_options(file)
  add_include_dir_for_file(obj_include_paths, file)
  dummy_dir = os.path.dirname(f'obj/dummies/{file_drop_extension(file)}')
  pathlib.Path(str(dummy_dir)).mkdir(parents = True, exist_ok = True)
  if options != None:
    add_module_for_file(file)
    module_name = file_module_name(file)
    fsti_map[module_name] = f'{file_drop_extension(to_obj_dir(file))}.fsti'
    for extension in ['.fst', '.fsti']:
      # The F* dependency analysis runs before .vaf files are converted to .fst/.fsti files,
      # so generate a dummy .fst/.fsti file pair for each .vaf file for the F* dependency analysis.
      dummy_file = File(f'obj/dummies/{file_drop_extension(file)}{extension}')
      pathlib.Path(os.path.dirname(dummy_file)).mkdir(parents = True, exist_ok = True)
      with open(str(dummy_file), 'w') as myfile:
        myfile.write(f'module {module_name}' + '\n')

def add_ml_dependencies(targets, sources):
  if fstar_extract:
    sources_ml = [ml_out_file(File(x), '.ml') for x in sources if is_our_file(File(x))]
    targets_ml = [ml_out_file(File(x), '.ml') for x in targets if is_our_file(File(x))]
    sources_ml = [x for x in sources_ml if not (x in no_extraction_files)]
    targets_ml = [x for x in targets_ml if not (x in no_extraction_files)]
    sources_ml = [x for x in sources_ml if not (x in targets_ml)]
    Depends(targets_ml, sources_ml)
    for t in targets_ml:
      if not (t in ml_out_deps):
        ml_out_deps[t] = set()
      for s in sources_ml:
        ml_out_deps[t].add(s)

# Verify a .fst or .fsti file
def verify_fstar_file(options, targetfile, sourcefile, fstar_includes):
  stderrfile = File(f'{targetfile}.stderr')
  temptargetfile = File(f'{targetfile}.tmp')
  temptargetfiles = [temptargetfile]
  dumptargetfile = File(re.sub('\.verified$', '.dump', str(targetfile)))
  hintfile = to_hint_file(sourcefile)
  if min_test and on_black_list(sourcefile, min_test_suite_blacklist):
    print(f'Skipping {sourcefile} because it is on min_test_suite_blacklist')
  if record_hints:
    temptargetfiles.append(hintfile)
  elif use_hints and os.path.isfile(str(hintfile)):
    Depends(temptargetfiles, hintfile)
  Command(temptargetfiles, sourcefile,
    f'{fstar_exe} {sourcefile} {options.verifier_flags} {fstar_z3_path} {fstar_no_verify}' +
    f' {fstar_includes} {" ".join(fstar_user_args)} --hint_file {hintfile} {fstar_record_hints}' +
    (f' --debug {file_module_name(File(sourcefile))} --debug_level print_normalized_terms' if profile else '') +
    f' 1> {temptargetfile} 2> {stderrfile}')
  CopyFile(targetfile, temptargetfile)
  dump_module_flag = '--dump_module ' + file_module_name(sourcefile)
  dump_flags = ('--print_implicits --print_universes --print_effect_args --print_full_names' +
    ' --print_bound_var_types --ugly ' + dump_module_flag)
  Command(dumptargetfile, sourcefile,
    f'{fstar_exe} {sourcefile} {options.verifier_flags} {fstar_z3_path} {fstar_no_verify} --admit_smt_queries true' +
    f' {fstar_includes} {" ".join(fstar_user_args)}' +
    f' {dump_flags} 1> {dumptargetfile} 2> {dumptargetfile}.stderr')
  Depends(dumptargetfile, targetfile)

def extract_fstar_file(options, sourcefile, fstar_includes):
  base_name = file_drop_extension(sourcefile)
  module_name = file_module_name(sourcefile)
  hintfile = to_hint_file(sourcefile)
  mlfile = ml_out_file(sourcefile, '.ml')
  Depends(mlfile, to_obj_dir(base_name + '.fst.verified'))
  verifier_flags = options.verifier_flags.replace('--use_extracted_interfaces true', '')
  return Command(mlfile, sourcefile,
    f'{fstar_exe} {sourcefile} {verifier_flags} {fstar_z3_path} {fstar_no_verify} --admit_smt_queries true' +
    f' {fstar_includes} {" ".join(fstar_user_args)}' +
    f' --odir obj/ml_out --codegen OCaml --extract_module {module_name}')

# Process a .fst or .fsti file
def process_fstar_file(file, fstar_includes):
  options = get_build_options(file)
  if options != None:
    target = File(f'{to_obj_dir(file)}.verified')
    verify_fstar_file(options, target, file, fstar_includes)
    if fstar_extract:
      if file_extension(file) == '.fst':
        if not (ml_out_file(file, '.ml') in no_extraction_files):
          extract_fstar_file(options, file, fstar_includes)

def vale_dependency_scan(file):
  with open(file) as f:
    contents = f.read()
  dirname = os.path.dirname(str(file))
  vaf_includes = vale_include_re.findall(contents)
  fst_includes = vale_open_re.findall(contents) + vale_import_re.findall(contents)
  fst_friends = vale_friend_re.findall(contents)
  obj_file_base = file_drop_extension(to_obj_dir(file))
  vaf_dump_deps[str(file)] = set()
  vaf_vaf_deps[str(file)] = set()
  fst_fsti = [f'{obj_file_base}.fst', f'{obj_file_base}.fsti']
  obj_tmp = [f'{obj_file_base}.fst.verified.tmp']
  obj_tmps = [f'{obj_file_base}.fst.verified.tmp', f'{obj_file_base}.fsti.verified.tmp']
  typesfile = File(f'{obj_file_base}.types.vaf')
  for (attrs, inc) in vaf_includes:
    if vale_fstar_re.search(attrs):
      dumpsourcebase = to_obj_dir(File(f'{fsti_map[inc]}'))
      dumpsourcefile = File(f'{dumpsourcebase}.dump')
      if is_our_file(dumpsourcebase):
        vaf_dump_deps[str(file)].add(str(dumpsourcefile))
      else:
        print_error_exit(f'TODO: not implemented: .vaf includes extern F* file {inc}')
    else:
      f = os.path.join('code' if vale_from_base_re.search(attrs) else dirname, inc)
      # if A.vaf includes B.vaf, then manually establish these dependencies:
      #   A.fst.verified.tmp  depends on B.fsti.verified
      #   A.fsti.verified.tmp depends on B.fsti.verified
      vaf_vaf_deps[str(file)].add(str(File(f)))
      f_base = file_drop_extension(to_obj_dir(File(f)))
      f_fsti = File(f_base + '.fsti.verified')
      Depends(obj_tmps, f_fsti)
      add_ml_dependencies([obj_file_base + '.fst'], [f_base + '.fst'])
  Depends(fst_fsti, typesfile)
  for inc in fst_includes:
    if inc in fsti_map:
      Depends(obj_tmps, to_obj_dir(File(f'{fsti_map[inc]}.verified')))
      add_ml_dependencies([obj_file_base + '.fst'], [fsti_map[inc]])
  for inc in fst_friends:
    if inc in fsti_map:
      Depends(obj_tmp, re.sub('\.fsti$', '.fst.verified', str(to_obj_dir(fsti_map[inc]))))
      add_ml_dependencies([obj_file_base + '.fst'], [fsti_map[inc]])

# Translate Vale .vaf to F* .fst/fsti pair
# Takes a source .vaf File node
# Returns list of File nodes representing the resulting .fst and .fsti files
def translate_vale_file(options, source_vaf):
  target = file_drop_extension(to_obj_dir(source_vaf))
  target_fst = File(target + '.fst')
  target_fsti = File(target + '.fsti')
  targets = [target_fst, target_fsti]
  opt_vale_includes = vale_includes if options.vale_includes == None else options.vale_includes
  types_include = ''
  types_include = f'-include {target}.types.vaf'
  Command(targets, source_vaf,
    f'{mono} {vale_exe} -fstarText -quickMods -typecheck {types_include} {opt_vale_includes}' +
    f' -in {source_vaf} -out {target_fst} -outi {target_fsti}' +
    f' {vale_scons_args} {" ".join(vale_user_args)}')
  return targets

# Process a .vaf file
def process_vale_file(file, fstar_includes):
  options = get_build_options(file)
  if options != None:
    vale_dependency_scan(file)
    fsts = translate_vale_file(options, file)
    fst = fsts[0]
    fsti = fsts[1]
    fst_options = get_build_options(fst)
    fsti_options = get_build_options(fsti)
    target = file_drop_extension(to_obj_dir(file))
    target_fst = f'{target}.fst.verified'
    target_fsti = f'{target}.fsti.verified'
    Depends(f'{target_fst}.tmp', target_fsti)
    verify_fstar_file(fst_options, target_fst, fst, fstar_includes)
    verify_fstar_file(fsti_options, target_fsti, fsti, fstar_includes)
    if fstar_extract:
      extract_fstar_file(fst_options, fst, fstar_includes)

def compute_module_types(source_vaf):
  source_base = file_drop_extension(to_obj_dir(File(source_vaf)))
  types_vaf = f'{source_base}.types.vaf'
  done = set()
  dumps = []
  def collect_dumps_in_order(x):
    if not (x in done):
      done.add(x)
      for y in sorted(dump_deps[x]):
        # if x depends on y, y must appear first
        collect_dumps_in_order(y)
      x_vaf = re.sub('\.dump$', '.types.vaf', x)
      Depends(types_vaf, x)
      dumps.append(x)
  for vaf in sorted(vaf_vaf_deps[source_vaf] | {source_vaf}):
    for x in sorted(vaf_dump_deps[vaf]):
      collect_dumps_in_order(x)
  dumps_string = " ".join(['-in ' + str(x) for x in dumps])
  Depends(types_vaf, import_fstar_types_exe)
  Command(types_vaf, dumps, f'{mono} {import_fstar_types_exe} {dumps_string} -out {types_vaf} > {types_vaf}.errors')

def recursive_glob(pattern):
  matches = []
  split = os.path.split(pattern) # [0] is the directory, [1] is the actual pattern
  platform_directory = split[0] #os.path.normpath(split[0])
  for d in os.listdir(platform_directory):
    if os.path.isdir(os.path.join(platform_directory, d)):
      newpattern = os.path.join(split[0], d, split[1])
      matches.append(recursive_glob(newpattern))
  files = glob.glob(pattern)
  matches.append(files)
  return [File(x) for x in Flatten(matches)]

# Verify *.fst, *.fsti, *.vaf files in a list of directories.  This enumerates
# all files in those trees, and creates verification targets for each,
# which in turn causes a dependency scan to verify all of their dependencies.
def process_files_in(directories):
  fsts = []
  fstis = []
  vafs = []
  for d in directories:
    fsts.extend(recursive_glob(d + '/*.fst'))
    fstis.extend(recursive_glob(d + '/*.fsti'))
    vafs.extend(recursive_glob(d + '/*.vaf'))
  # Compute include directories:
  for file in fsts:
    include_fstar_file(file)
  for file in fstis:
    include_fstar_file(file)
  for file in external_files:
    file_node = File(file.obj_name())
    fsti_map[file_module_name(file_node)] = file_node
  for file in vafs:
    include_vale_file(file)
  # Process and verify files:
  fstar_include_paths = compute_include_paths(src_include_paths, obj_include_paths, 'obj')
  fstar_includes = compute_includes(src_include_paths, obj_include_paths, 'obj')
  if is_single_vaf:
    process_vale_file(File(single_vaf), fstar_includes)
  else:
    for file in fsts:
      process_fstar_file(file, fstar_includes)
    for file in fstis:
      process_fstar_file(file, fstar_includes)
    for file in external_files:
      process_fstar_file(File(file.obj_name()), fstar_includes)
    for file in vafs:
      process_vale_file(file, fstar_includes)
    for target in manual_dependencies:
      Depends(target, manual_dependencies[target])

def extract_assembly_code(output_base_name, main_file, alg_files, cmdline_file):
  # OCaml depends on many libraries and executables; we have to assume they are in the user's PATH:
  main_ml = ml_out_file(main_file, '.ml')
  main_cmx = ml_out_file(main_file, '.cmx')
  main_exe = ml_out_file(main_file, '.exe')
  alg_mls = [ml_out_file(x, '.ml') for x in alg_files]
  alg_cmxs = [ml_out_file(x, '.cmx') for x in alg_files]
  cmdline_ml = ml_out_file(cmdline_file, '.ml')
  cmdline_cmx = ml_out_file(cmdline_file, '.cmx')
  #pointer_src = File('code/lib/util/FStar_Pointer_Base.ml')
  #pointer_ml = ml_out_file(pointer_src, '.ml')
  #pointer_cmx = ml_out_file(pointer_src, '.cmx')
  #CopyFile(pointer_ml, pointer_src)
  CopyFile(cmdline_ml, cmdline_file)
  CopyFile(main_ml, main_file)
  for alg_cmx in alg_cmxs:
    Depends(cmdline_cmx, alg_cmx)
    Depends(main_cmx, alg_cmx)
  Depends(cmdline_cmx, cmdline_ml)
  Depends(main_cmx, cmdline_cmx)
  Depends(main_cmx, main_ml)
  Depends(cmdline_cmx, ml_out_file('X64_Machine_s.fst', '.cmx'))
  Depends(cmdline_cmx, ml_out_file('X64_Vale_Decls.fst', '.cmx'))
  done = set()
  cmxs = []
  objs = []
  ignore_warnings = [ "8", # Warning 8: this pattern-matching is not exhaustive.
                     "20", # Warning 20: this argument will not be used by the function.
                     "26"] # Warning 26: unused variable
  ignore_warnings_str = "-w " + "".join(["-" + s for s in ignore_warnings])
  def add_cmx(x_ml):
    x_cmx = ml_out_file(x_ml, '.cmx')
    x_obj = ml_out_file(x_ml, '.o')
    cmx = Command([x_cmx, x_obj], x_ml,
      f'OCAMLPATH={File(fstar_path + "/bin")} ocamlfind ocamlopt -c -package fstarlib -o {x_cmx} {x_ml} -I obj/ml_out {ignore_warnings_str}')
    cmxs.append(x_cmx)
    objs.append(x_obj)
    Depends(main_exe, x_cmx)
    Depends(main_exe, x_obj)
  def collect_cmxs_in_order(x_ml):
    if not (x_ml in done):
      done.add(x_ml)
      for y_ml in sorted(ml_out_deps[x_ml]): # sorting makes the order deterministic, so scons doesn't needlessly rebuild
        # if x depends on y, y must appear first in ocaml link step
        Depends(ml_out_file(x_ml, '.cmx'), ml_out_file(y_ml, '.cmx'))
        collect_cmxs_in_order(y_ml)
      add_cmx(x_ml)
  for alg_ml in alg_mls:
    collect_cmxs_in_order(alg_ml)
  add_cmx(cmdline_ml)
  add_cmx(main_ml)
  cmxs_string = " ".join([str(cmx) for cmx in cmxs])
  Command(main_exe, cmxs + objs,
    f'OCAMLPATH={File(fstar_path + "/bin")} ocamlfind ocamlopt -linkpkg -package fstarlib {cmxs_string} -o {main_exe}')
  # Run executable to generate assembly files:
  output_target_base = 'obj/' + output_base_name
  def generate_asm(suffix, assembler, os):
    # TODO: cross-compilation support; note that platform.machine() does not
    # produce a consistent string across OSes
    target = output_target_base + "-x86_64" + suffix
    return Command(target, main_exe, f'{main_exe} {assembler} {os} > {target}')
  masm_win = generate_asm('-msvc.asm', 'MASM', 'Win')
  gcc_win = generate_asm('-mingw.S', 'GCC', 'Win')
  gcc_linux = generate_asm('-linux.S', 'GCC', 'Linux')
  gcc_macos = generate_asm('-darwin.S', 'GCC', 'MacOS')
  if sys.platform.startswith('linux'):
    return [gcc_linux, masm_win, gcc_win, gcc_macos]
  elif sys.platform == 'cygwin' or 'SHELL' in os.environ:
    return [gcc_win, masm_win, gcc_linux, gcc_macos]
  elif sys.platform == 'win32':
    return [masm_win, gcc_win, gcc_linux, gcc_macos]
  elif sys.platform == 'darwin':
    return [gcc_macos, gcc_win, masm_win, gcc_linux]
  else:
    print('Unsupported sys.platform value: ' + sys.platform)

##################################################################################################
#
#   FStar dependency analysis
#
##################################################################################################

def compute_fstar_deps(src_directories, fstar_includes):
  import subprocess
  # find all .fst, .fsti files in src_directories
  fst_files = []
  for d in src_directories:
    fst_files.extend(recursive_glob(d+'/*.fst'))
    fst_files.extend(recursive_glob(d+'/*.fsti'))
  # use fst_files to choose .fst and .fsti files that need dependency analysis
  files = []
  for f in fst_files:
    options = get_build_options(f)
    if options != None:
      files.append(f)
  # call fstar --dep make
  includes = []
  for include in fstar_includes:
    includes += ["--include", include]
  lines = []
  depsBackupFile = 'obj/fstarDepsBackup.d'
  args = ["--dep", "make"] + includes + files
  cmd = [fstar_exe] + args
  cmd = [str(x) for x in cmd]
  #print(" ".join(cmd))
  try:
    if not dump_args:
      print('F* dependency analysis starting')
    o = subprocess.check_output(cmd, stderr = subprocess.STDOUT).decode('ascii')
    if not dump_args:
      print('F* dependency analysis finished')
  except (subprocess.CalledProcessError) as e:
    print(f'F* dependency analysis: error: {e.output}')
    Exit(1)
  fstar_deps_ok = True
  lines = o.splitlines()
  for line in lines:
    if 'Warning:' in line:
      print(line)
      fstar_deps_ok = False
    if len(line) == 0:
      pass
    elif '(Warning ' in line:
      # example: "(Warning 307) logic qualifier is deprecated"
      pass
    else:
      # lines are of the form:
      #   a1.fst a2.fst ... : b1.fst b2.fst ...
      # we change this to:
      #   obj\...\a1.fst.verified obj\...\a2.fst.verified ... : b1.fst.verified b2.fst.verified ...
      # we ignore targets that we will not verify (e.g. F* standard libraries)
      targets, sources = line.split(': ', 1) # ': ', not ':', because of Windows drive letters
      sources = sources.split()
      targets = targets.split()
      obj_name = str(Dir('obj'))
      dummies_name = str(Dir('obj/dummies'))
      sources = [str(File(x)).replace(dummies_name, obj_name) for x in sources]
      targets = [str(File(x)).replace(dummies_name, obj_name) for x in targets]
      for source in sources:
        for target in targets:
          if target.startswith('specs') and (source.startswith('obj') or source.startswith('code')) and not dump_args:
            print(f'{yellow}Warning: file {target} in specs directory depends on file {source} outside specs directory{uncolor}')
      sources_ver = [to_obj_dir(File(re.sub('\.fst$', '.fst.verified', re.sub('\.fsti$', '.fsti.verified', x)))) for x in sources if is_our_file(File(x))]
      targets_ver = [to_obj_dir(File(re.sub('\.fst$', '.fst.verified.tmp', re.sub('\.fsti$', '.fsti.verified.tmp', x)))) for x in targets if is_our_file(File(x))]
      Depends(targets_ver, sources_ver)
      add_ml_dependencies(targets, sources)
      # Computing types from F* files
      # Dump F* types for for each of a1.fst a2.fst ... into a1.fst.dump, a2.fst.dump, ...
      # Targets that we don't verify go in obj/external
      for t in targets:
        if is_our_file(File(t)):
          dumptargetfile = str(to_obj_dir(t + '.dump'))
        else:
          # Compute types of an external module, assuming it was compiled with default arguments
          dumptargetfile = 'obj/external/' + os.path.split(t)[1] + '.dump'
          dump_module_flag = '--dump_module ' + file_module_name(File(t))
          dump_flags = ('--print_implicits --print_universes --print_effect_args --print_full_names' +
            ' --print_bound_var_types --ugly ' + dump_module_flag)
          Command(dumptargetfile, t,
            f'{fstar_exe} {t} {fstar_z3_path} {fstar_no_verify} --admit_smt_queries true' +
            f' {dump_flags} 1> {dumptargetfile} 2> {dumptargetfile}.stderr')
        if not (dumptargetfile in dump_deps):
          dump_deps[dumptargetfile] = set()
        for s in sources:
          if is_our_file(File(s)):
            dump_deps[dumptargetfile].add(str(to_obj_dir(s + '.dump')))
          else:
            dump_deps[dumptargetfile].add('obj/external/' + os.path.split(s)[1] + '.dump')
  if fstar_deps_ok:
    # Save results in depsBackupFile
    with open(depsBackupFile, 'w') as myfile:
      for line in lines:
        myfile.write(line + '\n')
  else:
    print('F* dependency analysis failed')
    Exit(1)

##################################################################################################
#
#   Top-level commands
#
##################################################################################################

# Create obj directory and any subdirectories needed during dependency analysis
# (SCons will create other subdirectories during build)
pathlib.Path('obj').mkdir(parents = True, exist_ok = True)
pathlib.Path('obj/external').mkdir(parents = True, exist_ok = True)
pathlib.Path('obj/cache_checked').mkdir(parents = True, exist_ok = True)
pathlib.Path('obj/ml_out').mkdir(parents = True, exist_ok = True)

# Check F*, Z3, and Vale versions
if not fstar_my_version:
  check_fstar_version()
if not z3_my_version:
  if not found_z3:
    print_error_exit('Could not find z3 executable.  Either put z3 in your path, or put it in the directory tools/Z3/, or use the --FSTARZ3=<z3-executable> option.')
  check_z3_version(fstar_z3)
if not vale_my_version:
  check_vale_version()

if out_make != None:
  make_file = open(out_make, 'w')

if out_scons != None:
  scons_file = open(out_scons, 'w')
  scons_file.write('def declare_all(env):\n')

# HACK: copy external files
for f in external_files:
  source = f.filename
  target = f.obj_name()
  shutil.copy2(source, target)
  checked_source = f'{source}.checked'
  if os.path.isfile(checked_source):
    shutil.copy2(str(checked_source), f'{target}.checked')
  else:
    print(f'External file {source}.checked does not exist -- please make F*, KreMLin, and hacl-star/specs first')

if not dump_args:
  print('Processing source files')
process_files_in(verify_paths)
if not is_single_vaf:
  compute_fstar_deps(verify_paths, compute_include_paths(src_include_paths, obj_include_paths, 'obj/dummies'))
  for x in vaf_dump_deps:
    compute_module_types(x)

if fstar_extract:
  # Build AES-GCM
  aesgcm_asm = extract_assembly_code('aesgcm', File('code/crypto/aes/x64/Main.ml'),
    [File('code/crypto/aes/x64/X64.GCMdecrypt.vaf')], File('code/lib/util/CmdLineParser.ml'))
  cpuid_asm = extract_assembly_code('cpuid', File('code/lib/util/x64/CpuidMain.ml'),
    [File('code/lib/util/x64/stdcalls/X64.Cpuidstdcall.vaf')], File('code/lib/util/CmdLineParser.ml'))
  sha256_asm = extract_assembly_code('sha256', File('code/crypto/sha/ShaMain.ml'),
    [File('code/thirdPartyPorts/OpenSSL/sha/X64.SHA.vaf')], File('code/lib/util/CmdLineParser.ml'))
  curve25519_asm = extract_assembly_code('curve25519', File('code/crypto/ecc/curve25519/Main25519.ml'), [
      File('code/thirdPartyPorts/rfc7748/curve25519/X64.FastUtil.vaf'),
      File('code/thirdPartyPorts/rfc7748/curve25519/X64.FastHybrid.vaf'),
      File('code/thirdPartyPorts/rfc7748/curve25519/X64.FastWide.vaf'),
      File('code/thirdPartyPorts/rfc7748/curve25519/X64.FastSqr.vaf'),
      File('code/thirdPartyPorts/rfc7748/curve25519/X64.FastMul.vaf')],
    File('code/lib/util/CmdLineParser.ml'))
  if target_arch == 'amd64':
    aesgcmasm_obj = Assemble('obj/aesgcmasm_openssl', aesgcm_asm[0])
    aesgcmtest_src = File('code/crypto/aes/x64/TestAesGcm.cpp')
    aesgcmtest_cpp = to_obj_dir(aesgcmtest_src)
    CopyFile(aesgcmtest_cpp, aesgcmtest_src)
    aesgcmtest_exe = Cpp(source = [aesgcmasm_obj, aesgcmtest_cpp], target = 'obj/TestAesGcm.exe')
    sha256asm_obj = Assemble('obj/sha256asm_openssl', sha256_asm[0])
    sha256test_src = File('code/crypto/sha/TestSha.cpp')
    sha256test_cpp = to_obj_dir(sha256test_src)
    CopyFile(sha256test_cpp, sha256test_src)
    sha256test_exe = Cpp(source = [sha256asm_obj, sha256test_cpp], target = 'obj/TestSha.exe')
    curve25519asm_obj = Assemble('obj/curve25519asm_openssl', curve25519_asm[0])
    curve25519test_src = File('code/crypto/ecc/curve25519/test_ecc.c')
    curve25519test_cpp = to_obj_dir(curve25519test_src)
    CopyFile(curve25519test_cpp, curve25519test_src)
    curve25519test_exe = Cc(source = [curve25519asm_obj, curve25519test_cpp], target = 'obj/TestEcc.exe')

if out_make != None:
  make_file.write(f'vale-all : \\\n')
  for s in all_targets:
    make_file.write(f'\t{s} \\\n')
  make_file.write('')
  make_file.close()

if out_scons != None:
  scons_file.close()

if dump_args:
  print_dump_args()

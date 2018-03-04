# -*- python -*-
#######################################################################################################################
#
# Tool: build.flavor
#
# Description: adds the --flavor command-line option and sets compiler/linker flags appropriately
#
# Command-line options:
#   --flavor={debug|ship}
#
#######################################################################################################################

from SCons.Script import AddOption, GetOption

# Add --flavor={debug|ship} command-line option
AddOption('--flavor', dest = 'flavor', default = 'release',
          nargs = 1, type = 'string', action = 'store',
          metavar = 'FLAVOR', help = 'build flavor: (one of {debug, release})')

def exists(env):
    return True

def generate(env):
    # Validate the --flavor option
    flavor = GetOption('flavor')
    if not (flavor in ['debug', 'release']):
        print("*** build-flavor: Invalid value for option '--flavor': '" + flavor + "'. Valid values are: ('debug', 'release')")
        Exit(1)
    if not GetOption('silent'):
        if GetOption('clean'):
            print('build.flavor: Cleaning ' + flavor + ' flavor...')
        else:
            print('build.flavor: Building ' + flavor + ' flavor...')


    # MSVC: Enable exception unwind semantics
    env.AppendUnique(CCFLAGS = ['/EHsc'])

    # MSVC: Compile for multi-threaded [debug] CRT
    env.AppendUnique(CCFLAGS = ['/MDd'] if flavor == 'debug' else ['/MD'])

    # Define _DEBUG or NDEBUG based on build flavor
    env.AppendUnique(CCFLAGS = ['/D_DEBUG'] if flavor == 'debug' else ['/DNDEBUG'])

    # MSVC: Geerate a PDB
    env.AppendUnique(LINKFLAGS = ['/DEBUG'])

    # MSVC: Enable optimizations in release mode
    if flavor == 'release':
        env.AppendUnique(CCFLAGS = ['/Ox', '/GL'])
        env.AppendUnique(LINKFLAGS = ['/LTCG'])
        env.AppendUnique(ARFLAGS = ['/LTCG'])

    # MSVC: Compiler warning level
    env.AppendUnique(CCFLAGS = ['/W1'])

    # MSVC: Enable extra debugging checks in debug mode
    #if flavor == 'debug':
    #    env.AppendUnique(CCFLAGS = ['/sdl'])

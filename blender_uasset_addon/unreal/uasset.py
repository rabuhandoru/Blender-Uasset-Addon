from ..util.io_util import *
from ..util.version import VersionInfo
from .uexp import Uexp
import ctypes as c

#classes for .uasset

#header of .uasset
class UassetHeader(c.LittleEndianStructure):
    HEAD = b'\xC1\x83\x2A\x9E'
    _pack_=1
    _fields_ = [ #193 bytes
        #("head", c.c_char*4), #Unreal Header (193,131,42,158)
        #("version", c.c_int32), #-version-1=6 or 7
        #("null", c.c_ubyte*16),
        ("uasset_size", c.c_uint32), #size of .uasset
        ("str_length", c.c_uint32), #5
        ("none", c.c_char*5), #'None '
        ("pkg_flags", c.c_uint32), # 00 20 00 00: unversioned header flag
        ("name_count", c.c_uint32),
        ("name_offset", c.c_uint32),
        ("null2", c.c_ubyte*8),
        ("export_count", c.c_uint32),
        ("export_offset", c.c_uint32),
        ("import_count", c.c_uint32),
        ("import_offset", c.c_uint32),
        ("end_to_export", c.c_uint32),
        ("null3", c.c_ubyte*16),
        ("guid_hash", c.c_char*16),
        ("unk2", c.c_uint32),
        ("padding_count", c.c_uint32),
        ("name_count2", c.c_uint32), #name count again?
        ("null4", c.c_ubyte*36),
        ("unk3", c.c_uint64),
        ("padding_offset", c.c_uint32), #file data offset - 4
        ("file_length", c.c_uint32), #.uasset + .uexp - 4
        ("null5", c.c_ubyte*12),
        ("file_data_count", c.c_uint32),
        ("file_data_offset", c.c_uint32)
    ]

    def read(f):
        header = UassetHeader()
        check(f.read(4), UassetHeader.HEAD)
        header.version = -read_int32(f)-1
        if header.version not in [6, 7]:
            raise RuntimeError('Unsupported header version. ({})'.format(header.version))
        header.null = f.read(16+4*(header.version>=7))
        f.readinto(header)
        header.unversioned = (header.pkg_flags & 8192)!=0
        if header.version>=7:
            header.unk_count = read_uint32(f)
            check(read_int32(f), -1)
            check(read_int32(f), -1)
        return header

    def write(f, header):
        f.write(UassetHeader.HEAD)
        write_int32(f, -header.version-1)
        f.write(header.null)
        f.write(header)
        if header.version>=7:
            write_uint32(f, header.unk_count)
            write_int32(f, -1)
            write_int32(f, -1)

    def print(self):
        print('Header info')
        print('  file size: {}'.format(self.uasset_size))
        print('  number of names: {}'.format(self.name_count))
        print('  name directory offset: 193')
        print('  number of exports: {}'.format(self.export_count))
        print('  export directory offset: {}'.format(self.export_offset))
        print('  number of imports: {}'.format(self.import_count))
        print('  import directory offset: {}'.format(self.import_offset))
        print('  end offset of export: {}'.format(self.end_to_export))
        print('  padding offset: {}'.format(self.padding_offset))
        print('  file length (uasset+uexp-4): {}'.format(self.file_length))
        print('  file data count: {}'.format(self.file_data_count))
        print('  file data offset: {}'.format(self.file_data_offset))

#import data of .uasset
class UassetImport(c.LittleEndianStructure): 
    _pack_=1
    _fields_ = [ #28 bytes
        ("parent_dir_id", c.c_uint64),
        ("class_id", c.c_uint64),
        ("parent_import_id", c.c_int32),
        ("name_id", c.c_uint32),
        ("unk", c.c_uint32),
    ]

    def __init__(self):
        self.material=False

    def read(f, version):
        imp = UassetImport()
        f.readinto(imp)
        if version=='5.0':
            imp.unk2 = read_uint32(f)
        return imp

    def write(self, f, version):
        f.write(self)
        if version=='5.0':
            write_uint32(f, self.unk2)

    def name_import(self, name_list):
        self.name = name_list[self.name_id]
        self.class_name = name_list[self.class_id]
        self.parent_dir = name_list[self.parent_dir_id]
        self.material=self.class_name in ['Material', 'MaterialInstanceConstant']
        return self.name

    def print(self, str = '', padding=2):
        pad = ' '*padding
        print(pad+str+': ' + self.name)
        print(pad+'  class: '+self.class_name)
        print(pad+'  parent dir: '+self.parent_dir)
        print(pad+'  parent import: ' + self.parent_name)

    def copy(self):
        copied = UassetImport()
        copied.parent_dir_id = self.parent_dir_id
        copied.class_id = self.class_id
        copied.parent_import_id = self.parent_import_id
        copied.name_id = self.name_id
        copied.unk = copied.unk
        copied.material = self.material
        return copied

def name_imports(imports, name_list):
    import_names = list(map(lambda x: x.name_import(name_list), imports))
    def name_parent(x):
        if x.parent_import_id==0:
            x.parent_name="None"
        else:
            x.parent_name = import_names[-x.parent_import_id-1]
    list(map(lambda x: name_parent(x), imports))
        
#export data of .uasset
class UassetExport(c.LittleEndianStructure): 
    _pack_=1
    _fields_ = [ #104 bytes
        ("class_id", c.c_int32),
        ("null", c.c_uint32),
        ("import_id", c.c_int32),
        ("null2", c.c_uint32),
        ("name_id", c.c_uint32),
        ("some", c.c_uint32),
        ("unk_int", c.c_uint32),
        ("size", c.c_uint64),
        ("offset", c.c_uint32),
        ("unk", c.c_ubyte*64),
    ]

    MAIN_EXPORTS=['SkeletalMesh', 'StaticMesh', 'Skeleton', 'Texture2D', 'TextureCube', 'Material', 'MaterialInstanceConstant']

    def read(f, version):
        exp = UassetExport()
        f.readinto(exp)
        if version=='5.0':
            exp.unk2 = read_uint32(f)
        return exp

    def write(self, f, version):
        f.write(self)
        if version=='5.0':
            write_uint32(f, self.unk2)

    def update(self, size, offset):
        self.size=size
        self.offset=offset

    def name_exports(exports, imports, name_list):
        asset_type=None
        for export in exports:
            export_import = imports[-export.import_id-1]
            export.import_name = export_import.name
            export.name=name_list[export.name_id]
            export.class_name = export_import.class_name
            if export.class_name in UassetExport.MAIN_EXPORTS:
                asset_type = export.class_name
                export.ignore=False
            else:
                export.ignore=True
        return asset_type

    def read_uexp(self, f):
        self.bin=f.read(self.size)

    def write_uexp(self, f):
        f.write(self.bin)

    def print(self, padding=2):
        pad=' '*padding
        print(pad+self.name)
        print(pad+'  class: {}'.format(self.class_name))
        print(pad+'  import: {}'.format(self.import_name))
        print(pad+'  size: {}'.format(self.size))
        print(pad+'  offset: {}'.format(self.offset))

class Uasset:

    def __init__(self, file, version='ff7r', ignore_uexp=False, asset_type='', verbose=False):
        ext = get_ext(file)
        base = file[:-len(ext)]
        if ext!='uasset':
            if ext!='uexp':
                raise RuntimeError('Not .uasset! ({})'.format(file))
            else:
                file = base+'uasset'

        print('Loading '+file+'...')

        self.actual_path = file
        self.file=os.path.basename(file)[:-7]
        self.name = os.path.splitext(os.path.basename(file))[0]
        if version=='ff7r':
            base_version='4.18'
            custom_version=version
        else:
            base_version=version
            custom_version=None
        self.version=VersionInfo(base_version, customized_version=custom_version)

        with open(file, 'rb') as f:
            self.size=get_size(f)
            #read header
            self.header=UassetHeader.read(f)
            self.unversioned=self.header.unversioned

            if verbose:
                print('size: {}'.format(self.size))
                self.header.print()
                print('Name list')
            
            #read name table
            def read_names(f, i):
                name = read_str(f)
                hash = f.read(4)
                if verbose:
                    print('  {}: {}'.format(i, name))
                return name, hash
            names = [read_names(f, i) for i in range(self.header.name_count)]
            self.name_list = [x[0] for x in names]
            self.hash_list = [x[1] for x in names]

            #read imports
            check(self.header.import_offset, f.tell(), f)
            self.imports=[UassetImport.read(f, self.version) for i in range(self.header.import_count)]
            name_imports(self.imports, self.name_list)
            if verbose:
                print('Import')
                [x.print(str(i)) for x,i in zip(self.imports, range(len(self.imports)))]

            paths = [n for n in self.name_list if n[0]=='/']
            import_names = list(set([imp.name for imp in self.imports] + [imp.parent_dir for imp in self.imports]))
            for imp in import_names:
                if imp in paths:
                    paths.remove(imp)
            if len(paths)!=1:
                print(paths)
                raise RuntimeError('Failed to get asset path.')
            self.asset_path = paths[0]

            #read exports
            check(self.header.export_offset, f.tell(), f)
            self.exports=[UassetExport.read(f, self.version) for i in range(self.header.export_count)]
            self.asset_type = UassetExport.name_exports(self.exports, self.imports, self.name_list)
            if self.asset_type is None:
                raise RuntimeError('Unsupported asset')
            if asset_type not in self.asset_type:
                raise RuntimeError('Not {}.'.format(asset_type))

            if verbose:
                print('Export')
                list(map(lambda x: x.print(), self.exports))
            check(self.header.end_to_export, f.tell())

            read_null_array(f, self.header.padding_count)
            check(self.header.padding_offset, f.tell())
            read_null(f)
            check(self.header.file_data_offset, f.tell())
            self.file_data_ids = read_int32_array(f, len=self.header.file_data_count)
            
            '''
            for i in self.file_data_ids:
                if i<0:
                    i = -i-1
                    print(self.imports[i].name)
                else:
                    print(i)
            '''

            check(f.tell(), self.size)
            check(self.header.uasset_size, self.size)

        if ignore_uexp:
            return
        
        self.uexp = Uexp(base+'uexp', self, verbose=verbose)
    
    def save(self, file):
        ext = get_ext(file)
        base = file[:-len(ext)]
        if ext!='uasset':
            if ext!='uexp':
                raise RuntimeError('Not .uasset! ({})'.format(file))
            else:
                file = base+'uasset'
        
        directory = os.path.dirname(file)
        if not os.path.exists(directory):
            mkdir(directory)

        uexp_file = base+'uexp'
        uexp_size = self.uexp.save(uexp_file)
        
        print('Saving '+file+'...')
        with open(file, 'wb') as f:
            #skip header part
            f.seek(self.header.name_offset)

            #self.header.name_offset = f.tell()
            self.header.name_count = len(self.name_list)
            self.header.name_count2 = len(self.name_list)
            #write name table
            if len(self.name_list)>len(self.hash_list):
                self.hash_list += [b'\x00'*4]*(len(self.name_list)-len(self.hash_list))
            for name, hash in zip(self.name_list, self.hash_list):
                write_str(f, name)
                f.write(hash)

            #write imports
            self.header.import_offset = f.tell()
            self.header.import_count = len(self.imports)
            list(map(lambda x: x.write(f, self.version), self.imports))

            #skip exports part
            self.header.export_offset = f.tell()
            self.header.export_count = len(self.exports)
            list(map(lambda x: x.write(f, self.version), self.exports))
            self.header.end_to_export = f.tell()

            #file data ids
            write_null_array(f, self.header.padding_count+1)
            self.header.padding_offset = f.tell()-4
            self.header.file_data_offset = f.tell()
            self.header.file_data_count = len(self.file_data_ids)
            write_int32_array(f, self.file_data_ids)
            self.header.uasset_size = f.tell()
            self.header.file_length=uexp_size+self.header.uasset_size-4
            
            #write header
            f.seek(0)
            UassetHeader.write(f, self.header)

            #write exports
            f.seek(self.header.export_offset)
            offset = self.header.uasset_size
            for export in self.exports:
                export.update(export.size, offset)
                offset+=export.size
            list(map(lambda x: x.write(f, self.version), self.exports))
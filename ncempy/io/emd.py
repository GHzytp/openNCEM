"""
This module provides an interface to the Berkeley EMD file format.

See https://emdatasets.com/ for more details.



"""

from pathlib import Path
import datetime

import numpy as np
import h5py


class fileEMD:
    """Class to represent EMD files.

    Implemented for spec 0.2 using the recommended layout for metadata.

    Meant to provide convenience functions for commonly occurring tasks. This means that you will still want to access
     fileEMD.file_hdl to manipulate the HDF5 file for not so commonly occurring tasks.

    Parameters
    ----------
        filename : str
            Name of the EMD file.
        readonly : bool, default True
            Set to False to allow writing to the file.

    Example
    -------
        Open an Berkeley EMD file. List the available data sets. Load a 3D data set and plot the first image.

            >>> from ncempy.io import emd
            >>> import matplotlib.pyplot as plt
            >>> emd1 = emd.fileEMD('filename.emd')
            >>> [print(dataGroup.name) for dataGroup in emd1.list_emds] # Use the builtin list_emds variable to print all available EMD datasets
            >>> data1,dims1 = emd1.get_emdgroup(emd1.list_emds[0]) # load the first full data array and dimension information
            >>> fg1,ax1 = plt.subplots(1,1)
            >>> ax1.imshow(data1[0,:,:],extent=(dims1[1][0][0],dims1[1][0][-1],dims1[2][0][0],dims1[2][0][-1])) # the extent uses the first and last array values of the dimension vectors
            >>> ax1.set(xlabel='{0[1]} ({0[2]})'.format(dims1[1]),ylabel='{0[1]} ({0[2]})'.format(dims1[2])) # label the axes with the name and units of each dimension vector
            >>> del emd1 #close the emd file
    """

    def __init__(self, filename, readonly=True):
        """Init opening/creating the file.

        """

        self.filename = filename
        self.readonly = readonly

        # necessary declarations in case something goes bad
        self.file_hdl = None
        self.version = None
        self.data = None
        self.microscope = None
        self.sample = None
        self.user = None
        self.comments = None
        self.list_emds = []  # list of HDF5 groups with emd_data_type type

        # check filename type
        if isinstance(filename, str):
            pass
        elif isinstance(filename, Path):
            filename = str(filename)
        else:
            raise TypeError('Filename is supposed to be a string or pathlib.Path')

        # try opening the file
        if readonly:
            try:
                self.file_hdl = h5py.File(filename, 'r')
            except:
                print('Error opening file for readonly: "{}"'.format(filename))
                raise
        else:
            try:
                self.file_hdl = h5py.File(filename, 'a')
            except:
                print('Error opening file for read/write: "{}"'.format(filename))
                raise

        # if we got a working file
        if self.file_hdl:
            # check version information
            self.check_version()

            # check for data group
            if 'data' not in self.file_hdl:
                if not readonly:
                    self.data = self.file_hdl.create_group('data')
            else:
                self.data = self.file_hdl['data']

            # check for data group
            if 'microscope' not in self.file_hdl:
                if not readonly:
                    self.microscope = self.file_hdl.create_group('microscope')
            else:
                self.microscope = self.file_hdl['microscope']

            # check for data group
            if 'sample' not in self.file_hdl:
                if not readonly:
                    self.sample = self.file_hdl.create_group('sample')
            else:
                self.sample = self.file_hdl['sample']

            # check for data group
            if 'user' not in self.file_hdl:
                if not readonly:
                    self.user = self.file_hdl.create_group('user')
            else:
                self.user = self.file_hdl['user']

            # check for data group
            if 'comments' not in self.file_hdl:
                if not readonly:
                    self.comments = self.file_hdl.create_group('comments')
            else:
                self.comments = self.file_hdl['comments']

            # find emd_data_type groups in the file
            self.list_emds = self.find_emdgroups(self.file_hdl)

    def __del__(self):
        """Destructor for EMD file object.

        """
        # close the file
        # if(not self.file_hdl.closed):
        self.file_hdl.close()

    def __enter__(self):
        """Implement python's with statement

        """
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        """Implement python's with statement
        and close the file via __del__()
        """
        self.__del__()
        return None

    def check_version(self):
        """Check the version of the EMD file. Set the version to 0.2 if it does not exist and the file
        is opened with readonly=False"""
        if 'version_major' in self.file_hdl.attrs and 'version_minor' in self.file_hdl.attrs:
            # read version information
            self.version = (self.file_hdl.attrs['version_major'], self.file_hdl.attrs['version_minor'])
            # compare to implementation
            if not self.version == (0, 2):
                print(
                    'WARNING: You are reading a version {}.{} EMD file, this implementation assumes version 0.2!'.format(
                        self.version[0], self.version[1]))
        else:
            # set version information to 0.2
            if not self.readonly:
                self.file_hdl.attrs['version_major'] = 0
                self.file_hdl.attrs['version_minor'] = 2

    def find_emdgroups(self, parent):
        """Find all emd_data_type groups within the group parent and return a list of references to their HDF5 groups.

        Parameters
        ----------
            parent: h5py._hl.group.Group
                Handle to the parent group.

        Returns
        -------
            : list
                A list of h5py._hl.group.Group handles to children groups
                being emd_data_type groups.

        """

        emds = []

        # recursive function to run and retrieve groups with emd_group_type set to 1
        def proc_group(group, emds):
            # take a look at each item in the group
            for item in group:
                # check if group
                if group.get(item, getclass=True) == h5py.Group:
                    item = group.get(item)
                    # check if emd_group_type
                    if 'emd_group_type' in item.attrs:
                        if item.attrs['emd_group_type'] == 1:
                            emds.append(item)
                    # process subgroups
                    proc_group(item, emds)

        # run
        proc_group(parent, emds)

        return emds

    def _get_dset_string(self, group):
        """All dset names will be data for v0.2"""
        return 'data'

    def get_emddims(self, group):
        """Get the emdtype dimensions saved in in group.

        Parameters
        ----------
            group: h5py._hl.group.Group
                Reference to the emdtype HDF5 group.

        Returns
        -------
            : tuple
                List of dimension vectors plus labels and units.

        """
        # get the dims
        dims = []
        for i in range(len(group[self._get_dset_string(group)].shape)):
            dim = group['dim{}'.format(i + 1)]
            # save them as (vector, name, units)

            if isinstance(dim.attrs['name'], np.ndarray):
                name = dim.attrs['name'][0]
            else:
                name = dim.attrs['name']

            if isinstance(dim.attrs['units'], np.ndarray):
                units = dim.attrs['units'][0]
            else:
                units = dim.attrs['units']

            dims.append((dim[:], name.decode('utf-8'), units.decode('utf-8')))

        dims = tuple(dims)
        return dims

    def get_emdgroup(self, group, memmap=False):
        """Get the emd data saved in the requested group.

        Parameters
        ----------
            group: h5py._hl.group.Group or int
                Reference to the HDF5 group to load. If int is used then the item corresponding to self.list_emds
                is loaded
            memmap: bool
                Return the data as a memmap instead of loading everything into memory

        Returns
        -------
            : tuple/None
                None or tuple containing:

                : np.ndarray
                    The data of the emdtype group.

                : list
                    List of [0] dimension vectors, [1] labels and [2] units.

        """

        # check input
        if not isinstance(group, h5py.Group):
            if isinstance(group, int):
                try:
                    group = self.list_emds[group]
                except IndexError:
                    print('group does not exist')
                    return
            else:
                raise TypeError('group needs to refer to a valid HDF5 group!')

        if not 'emd_group_type' in group.attrs:
            raise TypeError('group is not a emd_group_type group!')
        if not group.attrs['emd_group_type'] == 1:
            raise TypeError('group is not a emd_group_type group!')

        # retrieve data
        try:
            # get the data
            if memmap:
                data = group[self._get_dset_string(group)]
            else:
                data = group[self._get_dset_string(group)][:]

            # get the dimensions.
            dims = self.get_emddims(group)

            return data, dims
        except:
            # if something goes wrong, return None
            print('Content of "{}" does not seem to be in emd specified shape'.format(group.name))

            return None

    def write_dim(self, label, dim, parent):
        """Auxiliary function to write a dim dataset to parent.

        Input is not checked for sanity, so handle exceptions in call.

        Parameters
        ----------
            label: str
                Label for dataset, usually dim1, dim2, dimN.
            dim: tuple
                Tuple containing (data, name, units).
            parent: h5py.Group
                HDF5 handle to parent group.

        Returns
        -------
            : h5py.Group
                HDF5 dataset handle referencing this dim.
        """

        try:
            dset = parent.create_dataset(label, data=dim[0])
            dset.attrs['name'] = np.string_(dim[1])
            dset.attrs['units'] = np.string_(dim[2])
        except:
            raise RuntimeError('Error during writing dim dataset')

        return dset

    def put_emdgroup(self, label, data, dims, parent=None, overwrite=False, **kwargs):
        """Put an emdtype dataset into the EMD file.

        Parameters
        ----------
            label: str
                Label for the emdtype group containing the dataset.
            data: np.ndarray
                Numpy array containing the data.
            dims: tuple
                Tuple containing the necessary dims as ((vec, name, units), (vec, name, units), ...)
            parent: h5py._hl.group.Group/None
                Parent for the emdtype group, if None it will be written to /data.
            overwrite: bool
                Set to force overwriting entry in EMD file.
            **kwargs: various
                Keyword arguments to be passed to h5py.create_dataset(), e.g. for compression.

        Returns
        -------
            : h5py._hl.group.Group/None
                Group referencing this emdtype dataset or None if failed.
        """

        # check input
        if not isinstance(label, str):
            raise TypeError('label needs to be string!')

        if not isinstance(data, np.ndarray):
            raise TypeError('data needs to be a numpy.ndarray!')

        try:
            assert len(dims) == len(data.shape)
            for i in range(len(dims)):
                assert len(dims[i]) == 3
                assert dims[i][0].shape[0] == data.shape[i]
        except:
            raise TypeError('Something wrong with the provided dims')

        # write stuff to HDF5

        # create group
        try:
            if parent:
                if label in parent:
                    if overwrite:
                        print('overwriting "{}" in "{}"'.format(label, parent.name))
                        del parent[label]
                    else:
                        print('"{}" already exists in "{}"'.format(label, parent.name))
                        raise RuntimeError('"{}" already exists in "{}"'.format(label, parent.name))
                grp = parent.create_group(label)

            else:
                if label in self.data:
                    if overwrite:
                        print('overwriting "{}" in "{}"'.format(label, self.data.name))
                        del self.data[label]
                    else:
                        print('"{}" already exists in "{}"'.format(label, self.data.name))
                        raise RuntimeError('"{}" already exists in "{}"'.format(label, self.data.name))

                grp = self.data.create_group(label)

            # add attribute
            grp.attrs['emd_group_type'] = 1

            # create dataset
            _ = grp.create_dataset('data', data=data, **kwargs)

            # create dim datasets
            for i in range(len(dims)):
                self.write_dim(dims[i], grp)

            # update emds list
            self.list_emds = self.find_emdgroups(self.file_hdl)

            return grp
        except:
            print('Something went wrong trying to write the dataset.')

            return None

    def put_comment(self, msg, timestamp=None):
        """Create a comment in the EMD file.

        If timestamp already exists, the msg is appended to existing comment.

        Parameters
        ----------
            msg: str
                String of the message to save.
            timestamp: str/None
                Timestamp used as the key, defaults to the current UTC time.

        """

        # check input
        if not isinstance(msg, str):
            raise TypeError('msg needs to be a string!')

        # create timestamp if missing
        if not timestamp:
            timestamp = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S (UTC)')
        else:
            # try to convert given timestamp to string
            try:
                timestamp = str(timestamp)
            except:
                raise

        # write comment
        if timestamp in self.comments.attrs:
            # append to existing
            self.comments.attrs[timestamp] += np.string_('\n' + msg)

        else:
            # create new entry
            self.comments.attrs[timestamp] = np.string_(msg)
            
    def get_memmap(self, group):
        """ Get the emd group data as a memmap so that the data
        is not loaded into memory. Essentially calls get_emdgroup()
        with the keyword memmap keyord equals True.
        
        See get_emdgroup() for parameters and return values.
        
        
        """
        return self.get_emdgroup(group, memmap=True)
        

def defaultDims(data, pixel_size=None):
    """ A helper function that can generate a properly setup dim tuple
    with default values to allow quick writing of EMD files without
    the need to create these dim vectors manually.

    Parameters
    ----------
        data : ndarray
            The data that will be written to the EMD file. This is used to get the number of dims and their shape

        pixel_size : tuple, optional
            A tuple of pixel sizes. Must have same length as the number of dimensions of data.

    Returns
    -------
        dims: list
            A properly formatted tuple of dim vectors used as input
            to emd.emdFile.put_emdgroup()
    """
    if isinstance(pixel_size, np.ndarray):
        raise Exception('pixel_size must be a tuple')

    num = data.ndim

    if not pixel_size:
        pixel_size = (1,) * num

    if len(pixel_size) != data.ndim:
        raise ValueError('pixel_size and data dimensions must match')

    dims = []
    for ii in range(num):
        curDim = [np.linspace(0, data.shape[ii] - 1, data.shape[ii]) * pixel_size[ii],
                  'dim{}'.format(ii+1), 'unit{}'.format(ii+1)]
        dims.append(curDim)

    return dims


class fileEMD_v05(fileEMD):
    """ Subclass fileEMD to read v0.5"""

    def __init__(self, filename, *args, **kwargs):
        super(fileEMD_v05, self).__init__(filename, readonly=True)

    def check_version(self):
        """Check version information. Sets version information if not set"""
        if 'version_major' in self.file_hdl.attrs and 'version_minor' in self.file_hdl.attrs:
            # read version information
            self.version = (self.file_hdl.attrs['version_major'], self.file_hdl.attrs['version_minor'])
            # compare to implementation
            if not self.version == (0, 5):
                print('WARNING: You are reading a version {}.{} EMD file,'
                      'this implementation assumes version 0.5!'.format(self.version[0], self.version[1]))

    def _get_dset_string(self, group):
        """dset names depend on the parent emd group name"""
        parent_name = group.name.split('/')[-2]
        if parent_name == 'datacubes':
            return 'datacube'
        elif parent_name == 'diffractionslices':
            return 'diffractionslice'
        elif parent_name == 'pointlistarrayss':
            return 'pointlistarray'
        elif parent_name == 'pointlists':
            return 'pointlist'
        elif parent_name == 'realslices':
            return 'realslice'
        else:
            raise ValueError('dset name not supported')


def emdReader(filename, dsetNum=0):
    """ A simple helper function to read in the data and metadata 
    in a structured format similar to the other ncempy readers.

    Note
    ----
        Note fully implemented yet. Work in progress.

    Parameters
    ----------
        filename : str or pathlib.Path
            The path to the file as a string.
        dsetNum : int
            The index of the data set to load.
            
    Returns
    -------
        : dict
            Data and metadata as a dictionary similar to other ncempy readers.

    Example
    -------
        Simply load all data and metadata from a data set in an EMD Velox file
            >> import ncempy.io as nio
            >> emd0 = nio.emd.emdReader('filename.emd', dsetNum = 0)

    """

    with h5py.File(filename, 'r') as f0:
        if 'version_major' in f0.attrs and 'version_minor' in f0.attrs:
            # read version information
            version = (f0.attrs['version_major'], f0.attrs['version_minor'])
        elif '4DSTEM_simulation' in f0 or '4DSTEM_experiment' in f0:
            root_name = [ii for ii in f0.keys()][0]
            version = (f0[root_name].attrs['version_major'], f0[root_name].attrs['version_minor'])
        else:
            version = (0, 2)

    if version == (0, 5):
        emd_class = fileEMD_v05
    else:
        emd_class = fileEMD

    with emd_class(filename, readonly=True) as emd0:
        print(emd0)
        d, dims = emd0.get_emdgroup(dsetNum, memmap=False)  # memmap must be false. File is closed
        out = {'data': d, 'filename': filename, 'pixelSize': []}

        for dim in dims:
            try:
                d = dim[0][1] - dim[0][0]
            except:
                d = 0
            out['pixelSize'].append(d)
        out['pixelUnit'] = [aa[2] for aa in dims]
        out['pixelName'] = [aa[1] for aa in dims]
        return out


if __name__ == '__main__':
    fPath = Path(r'C:\Users\linol\data\LiPF6 multislice') / Path('XYZ_DEC_LiPF6_liquid_1M_small_eq_rot_crop.h5')

    #with fileEMD_v05(fPath) as emd00:
    #    print(emd00.list_emds)
    #    aa0 = emd00.get_emdgroup(0)
    #    bb0, bb_dims = emd00.get_memmap(0)

    #emd000 = emdReader(fPath, dsetNum=0)
    #print(emd000.keys())

    with fileEMD('c:/users/linol/temp.emd',readonly=False) as emd1:
        data = np.zeros((10, 10))
        dims = defaultDims(data,(1,1))
        emd1.put_emdgroup('temp', data, dims)

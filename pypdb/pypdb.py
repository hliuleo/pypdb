'''
PyPDB: A Python API for the RCSB Protein Data Bank
-----

GitHub: https://github.com/williamgilpin/pypdb

Documentation: http://williamgilpin.github.io/pypdb_docs/html

PyPI: https://pypi.python.org/pypi/pypdb

Please heed the PyPDB's MIT license, as well as those
of its dependencies: matplotlib, numpy, and xmltodict
'''

from matplotlib.pyplot import *
from numpy import *

from collections import OrderedDict, Counter
from itertools import repeat, chain
import urllib.request
import re
from json import loads, dumps
import warnings

import xmltodict

try:
    from bs4 import BeautifulSoup
except ImportError:
    try:
        import BeautifulSoup
    except ImportError:
        print ("pypdb can't find BeautifulSoup. You cannot parse BLAST search results without this module")

'''
=================
Functions for searching the RCSB PDB for lists of PDB IDs
=================
'''

# functions for conducting searches and obtaining lists of PDB ids
def make_query(search_term, querytype='AdvancedKeywordQuery'):
    ''' Repackage strings into a search dictionary

    This function takes a list of search terms and specifications
    and repackages it as a dictionary object that can be used to conduct a search

    Parameters
    ----------
    search_term : str 
    
        The specific term to search in the database. For specific query types,
        the strings that will yield valid results are limited to:

        'HoldingsQuery' : A Ggeneral search of the metadata associated with PDB IDs

        'ExpTypeQuery' : Experimental Method such as 'X-RAY', 'SOLID-STATE NMR', etc  

        'AdvancedKeywordQuery' : Any string that appears in the title or abstract

        'StructureIdQuery' :  Perform a search for a specific Structure ID

        'ModifiedStructuresQuery' : Search for related structures

        'AdvancedAuthorQuery' : Search by the names of authors associated with entries

        'MotifQuery' : Search for a specific motif

        'NoLigandQuery' : Find full list of PDB IDs without free ligrands
    
    querytype : str
    
        The type of query to perform, the easiest is an AdvancedKeywordQuery but more
        specific types of searches may also be performed

    Returns
    -------
        
    scan_params : dict
        
        A dictionary representing the query


    Examples
    --------
    This method usually gets used in tandem with do_search
    
    >>> a = make_query('actin network')
    >>> print (a)
    {'orgPdbQuery': {'description': 'Text Search for: actin',
    'keywords': 'actin',
    'queryType': 'AdvancedKeywordQuery'}}


    >>> search_dict = make_query('actin network')
    >>> found_pdbs = do_search(search_dict)
    >>> print(found_pdbs)
    ['1D7M', '3W3D', '4A7H', '4A7L', '4A7N']

    >>> search_dict = make_query('T[AG]AGGY',querytype='MotifQuery')
    >>> found_pdbs = do_search(search_dict)
    >>> print(found_pdbs)
    ['3LEZ', '3SGH', '4F47']

    '''
    assert querytype in {'HoldingsQuery', 'ExpTypeQuery',
                         'AdvancedKeywordQuery','StructureIdQuery',
                         'ModifiedStructuresQuery', 'AdvancedAuthorQuery', 'MotifQuery',
                         'NoLigandQuery'
                        }
  
    query_params = dict()
    query_params['queryType'] = querytype
    
    if querytype=='AdvancedKeywordQuery':
        query_params['description'] = 'Text Search for: '+ search_term
        query_params['keywords'] = search_term
        
    elif querytype=='NoLigandQuery':
        query_params['haveLigands'] = 'yes'
    
    elif querytype=='AdvancedAuthorQuery':
        query_params['description'] = 'Author Name: '+ search_term
        query_params['searchType'] = 'All Authors'
        query_params['audit_author.name'] = search_term
        query_params['exactMatch'] = 'false'
    
    elif querytype=='MotifQuery':
        query_params['description'] = 'Motif Query For: '+ search_term
        query_params['motif'] = search_term
    
    # search for a specific structure
    elif querytype in ['StructureIdQuery','ModifiedStructuresQuery']:
        query_params['structureIdList'] = search_term
    
        
    elif querytype=='ExpTypeQuery':
        query_params['experimentalMethod'] = search_term
        query_params['description'] = 'Experimental Method Search : Experimental Method='+ search_term
        query_params['mvStructure.expMethod.value']= search_term
        
    
    scan_params = dict()
    scan_params['orgPdbQuery'] = query_params
    
    
    return scan_params

def do_search(scan_params):
    '''Convert dict() to XML object an then send query to the RCSB PDB

    This function takes a valid query dict() object, converts it to XML,
    and then sends a request to the PDB for a list of IDs corresponding to search results
    
    Parameters
    ----------
    
    scan_params : dict
        A dictionary of query attributes to use for
        the search of the PDB
    
    
    Returns
    -------
    
    idlist : list
        A list of PDB ids returned by the search

    Examples
    --------
    This method usually gets used in tandem with make_query

    >>> a = make_query('actin network')
    >>> print (a)
    {'orgPdbQuery': {'description': 'Text Search for: actin',
    'keywords': 'actin',
    'queryType': 'AdvancedKeywordQuery'}}


    >>> search_dict = make_query('actin network')
    >>> found_pdbs = do_search(search_dict)
    >>> print(found_pdbs)
    ['1D7M', '3W3D', '4A7H', '4A7L', '4A7N']

    >>> search_dict = make_query('T[AG]AGGY',querytype='MotifQuery')
    >>> found_pdbs = do_search(search_dict)
    >>> print(found_pdbs)
    ['3LEZ', '3SGH', '4F47']
    '''
    
    url = 'http://www.rcsb.org/pdb/rest/search'

    queryText = xmltodict.unparse(scan_params, pretty=False)
    queryText = queryText.encode()

    req = urllib.request.Request(url, data=queryText)
    f = urllib.request.urlopen(req)
    result = f.read()

    if not result:
        warnings.warn('No results were obtained for this search')

    idlist = str(result)
    idlist =idlist.split('\\n')
    idlist[0] = idlist[0][-4:]
    kk = idlist.pop(-1)
    
    return idlist

def do_protsym_search(point_group, min_rmsd=0.0, max_rmsd=7.0):
    '''Performs a protein symmetry search of the PDB

    This function can search the Protein Data Bank based on how closely entries
    match the user-specified symmetry group

    Parameters
    ----------

    point_group : str
        The name of the symmetry point group to search. This includes all the standard
        abbreviations for symmetry point groups (e.g., C1, C2, D2, T, O, I, H, A1)

    min_rmsd : float
        The smallest allowed total deviation (in Angstroms) for a result to be classified
        as having a matching symmetry

    max_rmsd : float
        The largest allowed total deviation (in Angstroms) for a result to be classified
        as having a matching symmetry


    Returns
    -------

    idlist : list of strings
        A list of PDB IDs resulting from the search

    Examples
    --------

    >>> kk = do_protsym_search('C9', min_rmsd=0.0, max_rmsd=1.0)
    >>> print(kk[:5])
    ['1KZU', '1NKZ', '2FKW', '3B8M', '3B8N']

    '''

    query_params = dict()
    query_params['queryType'] = 'PointGroupQuery'
    query_params['rMSDComparator'] = 'between'

    query_params['pointGroup'] = point_group
    query_params['rMSDMin'] = min_rmsd
    query_params['rMSDMax'] = max_rmsd

    scan_params = dict()
    scan_params['orgPdbQuery'] = query_params
    idlist =  do_search(scan_params)
    return idlist



# functions for obtaining information about PDB id files
def get_all():
    """Return a list of all PDB entries currently in the RCSB Protein Data Bank
    
    Returns
    -------

    out : list of str
        A list of all of the PDB IDs currently in the RCSB PDB

    Examples
    --------

    >>> print(get_all()[:10])
    ['100D', '101D', '101M', '102D', '102L', '102M', '103D', '103L', '103M', '104D']

    """
    
    url = 'http://www.rcsb.org/pdb/rest/getCurrent'
    
    req = urllib.request.Request(url)
    f = urllib.request.urlopen(req)
    result = f.read()
    assert result
    
    kk = str(result)

    p = re.compile('structureId=\"...."')
    matches = p.findall(str(result))
    out = list()
    for item in matches:
        out.append(item[-5:-1])

    return out

'''
=================
Functions for looking up information given PDB ID
=================
'''

def get_info(pdb_id, url_root='http://www.rcsb.org/pdb/rest/describeMol?structureId='):
    '''Look up all information about a given PDB ID
    
    Parameters
    ----------

    pdb_id : string
        A 4 character string giving a pdb entry of interest
        
    url_root : string
        The string root of the specific url for the request type
        
    Returns
    -------
    
    out : OrderedDict
        An ordered dictionary object corresponding to bare xml
        
    '''
    
    url = url_root + pdb_id
    req = urllib.request.Request(url)
    f = urllib.request.urlopen(req)
    result = f.read()
    assert result
    
    out = xmltodict.parse(result,process_namespaces=True)
    
    return out

def get_pdb_file(pdb_id, filetype='pdb', compression=False):
    '''Get the full PDB file associated with a PDB_ID

    Parameters
    ----------

    pdb_id : string
        A 4 character string giving a pdb entry of interest

    filetype: string
        The file type. 
        'pdb' is the older file format, 
        'cif' is the newer replacement.
        'xml' an also be obtained and parsed using the various xml tools included in PyPDB
        'structfact' is a test file containing structure information for certain entries
    
    compression : bool
        Retrieve a compressed (gz) version of the file

    Returns
    -------

    result : string
        The string representing the full PDB file in the given format

    http://www.rcsb.org/pdb/download/downloadFile.do?fileFormat=structfact&structureId=2F5N

    Examples
    --------
    >>> pdb_file = get_pdb_file('4lza', filetype='cif', compression=True)
    >>> print(pdb_file[:200])
    data_4LZA
    # 
    _entry.id   4LZA 
    # 
    _audit_conform.dict_name       mmcif_pdbx.dic 
    _audit_conform.dict_version    4.032 
    _audit_conform.dict_location   http://mmcif.pdb.org/dictionaries/ascii/mmcif_pdbx

    DEV NOTE:
    http://www.rcsb.org/pdb/files/2F5N.pdb1.gz

    '''

    fullurl = 'http://www.rcsb.org/pdb/download/downloadFile.do?fileFormat='
    fullurl += filetype

    if compression:
        fullurl += '&compression=YES'
    else:
        fullurl += '&compression=NO'

    fullurl += '&structureId=' + pdb_id
    # url = 'http://www.rcsb.org/pdb/files/'+pdb_id+'.pdb'
    req = urllib.request.Request(fullurl)
    f = urllib.request.urlopen(req)
    result = f.read()
    result = result.decode('unicode_escape')

    return result

 
def get_all_info(pdb_id):
    '''A wrapper for get_info that cleans up the output slighly

    Parameters
    ----------

    pdb_id : string
        A 4 character string giving a pdb entry of interest
    
    Returns
    -------

    out : dict
        A dictionary containing all the information stored in the entry

    Examples
    --------

    >>> all_info = get_all_info('4lza')
    >>> print(all_info)
    {'polymer': {'macroMolecule': {'@name': 'Adenine phosphoribosyltransferase', '
    accession': {'@id': 'B0K969'}}, '@entityNr': '1', '@type': 'protein', 
    'polymerDescription': {'@description': 'Adenine phosphoribosyltransferase'}, 
    'synonym': {'@name': 'APRT'}, '@length': '195', 'enzClass': {'@ec': '2.4.2.7'}, 
    'chain': [{'@id': 'A'}, {'@id': 'B'}], 
    'Taxonomy': {'@name': 'Thermoanaerobacter pseudethanolicus ATCC 33223', 
    '@id': '340099'}, '@weight': '22023.9'}, 'id': '4LZA'}

    >>> results = get_all_info('2F5N')
    >>> first_polymer = results['polymer'][0]
    >>> first_polymer['polymerDescription']
    {'@description': "5'-D(*AP*GP*GP*TP*AP*GP*AP*CP*CP*TP*GP*GP*AP*CP*GP*C)-3'"}

    ''' 
    out = to_dict( get_info(pdb_id) )['molDescription']['structureId']
    out = remove_at_sign(out)
    return out

def get_raw_blast(pdb_id, output_form='HTML', chain_id='A'):
    '''Look up full BLAST page for a given PDB ID
        
    get_blast() uses this function internally
    
    Parameters
    ----------

    pdb_id : string
        A 4 character string giving a pdb entry of interest

    chain_id : string
        A single character designating the chain ID of interest

        
    output_form : string
        TXT, HTML, or XML formatting of the outputs
        
    Returns
    -------
    
    out : OrderedDict
        An ordered dictionary object corresponding to bare xml
        
    '''

    url_root = 'http://www.rcsb.org/pdb/rest/getBlastPDB2?structureId='
    url = url_root + pdb_id + '&chainId='+ chain_id +'&outputFormat=' + output_form
    req = urllib.request.Request(url)
    f = urllib.request.urlopen(req)
    result = f.read()
    result = result.decode('unicode_escape')
    assert result
    
    return result


def parse_blast(blast_string):
    '''Clean up HTML BLAST results

    This function requires BeautifulSoup and the re module
    It goes throught the complicated output returned by the BLAST
    search and provides a list of matches, as well as the raw 
    text file showing the alignments for each of the matches.

    This function works best with HTML formatted Inputs
    ------
    
    get_blast() uses this function internally
    
    Parameters
    ----------
    
    blast_string : str
        A complete webpage of standard BLAST results
        
    Returns
    -------
    
    out : 2-tuple
        A tuple consisting of a list of PDB matches, and a list
        of their alignment text files (unformatted)
    
    
    '''
    
    soup = BeautifulSoup(str(blast_string), "html.parser")
    
    all_blasts = list()
    all_blast_ids = list()

    pattern = '></a>....:'
    prog = re.compile(pattern)

    for item in soup.find_all('pre'):
        if len(item.find_all('a'))==1:
            all_blasts.append(item)
            blast_id = re.findall(pattern, str(item) )[0][-5:-1]
            all_blast_ids.append(blast_id)
        
    out = (all_blast_ids, all_blasts)
    return out


def get_blast2(pdb_id, chain_id='A', output_form='HTML'):
    '''Alternative way to look up BLAST for a given PDB ID. This function is a wrapper
    for get_raw_blast and parse_blast
    
    Parameters
    ----------
    pdb_id : string
        A 4 character string giving a pdb entry of interest

    chain_id : string
        A single character designating the chain ID of interest

    output_form : string
        TXT, HTML, or XML formatting of the BLAST page
        
    Returns
    -------
    
    out : 2-tuple
        A tuple consisting of a list of PDB matches, and a list
        of their alignment text files (unformatted)


    Examples
    --------

    >>> blast_results = get_blast2('2F5N', chain_id='A', output_form='HTML')
    >>> print('Total Results: ' + str(len(blast_results[0])) +'\n')
    >>> print(blast_results[1][0])
    Total Results: 84
    <pre>
    &gt;<a name="45354"></a>2F5P:3:A|pdbid|entity|chain(s)|sequence
              Length = 274
     Score =  545 bits (1404), Expect = e-155,   Method: Composition-based stats.
     Identities = 274/274 (100%), Positives = 274/274 (100%)
    Query: 1   MPELPEVETIRRTLLPLIVGKTIEDVRIFWPNIIRHPRDSEAFAARMIGQTVRGLERRGK 60
               MPELPEVETIRRTLLPLIVGKTIEDVRIFWPNIIRHPRDSEAFAARMIGQTVRGLERRGK
    Sbjct: 1   MPELPEVETIRRTLLPLIVGKTIEDVRIFWPNIIRHPRDSEAFAARMIGQTVRGLERRGK 60
    ...
        
    '''

    raw_results = get_raw_blast(pdb_id, chain_id=chain_id, output_form=output_form)
    out = parse_blast(raw_results)
    
    return out

def describe_pdb(pdb_id):
    """Get description and metadata of a PDB entry

    Parameters
    ----------

    pdb_id : string
        A 4 character string giving a pdb entry of interest
    
    Returns
    -------
    out : string
        A text pdb description from PDB

    Examples
    --------

    >>> describe_pdb('4lza')
    {'citation_authors': 'Malashkevich, V.N., Bhosle, R., Toro, R., Hillerich, B., Gizzi, A., Garforth, S., Kar, A., Chan, M.K., Lafluer, J., Patel, H., Matikainen, B., Chamala, S., Lim, S., Celikgil, A., Villegas, G., Evans, B., Love, J., Fiser, A., Khafizov, K., Seidel, R., Bonanno, J.B., Almo, S.C.',
     'deposition_date': '2013-07-31',
     'expMethod': 'X-RAY DIFFRACTION',
     'keywords': 'TRANSFERASE',
     'last_modification_date': '2013-08-14',
     'nr_atoms': '0',
     'nr_entities': '1',
     'nr_residues': '390',
     'release_date': '2013-08-14',
     'resolution': '1.84',
     'status': 'CURRENT',
     'structureId': '4LZA',
     'structure_authors': 'Malashkevich, V.N., Bhosle, R., Toro, R., Hillerich, B., Gizzi, A., Garforth, S., Kar, A., Chan, M.K., Lafluer, J., Patel, H., Matikainen, B., Chamala, S., Lim, S., Celikgil, A., Villegas, G., Evans, B., Love, J., Fiser, A., Khafizov, K., Seidel, R., Bonanno, J.B., Almo, S.C., New York Structural Genomics Research Consortium (NYSGRC)',
     'title': 'Crystal structure of adenine phosphoribosyltransferase from Thermoanaerobacter pseudethanolicus ATCC 33223, NYSGRC Target 029700.'}

    """
    out = get_info(pdb_id, url_root = 'http://www.rcsb.org/pdb/rest/describePDB?structureId=')
    out = to_dict(out)
    out = remove_at_sign(out['PDBdescription']['PDB'])
    return out

def get_entity_info(pdb_id):
    """Return pdb id information

    Parameters
    ----------

    pdb_id : string
        A 4 character string giving a pdb entry of interest

    Returns
    -------

    out : dict
        A dictionary containing a description the entry

    Examples
    --------
    >>> get_entity_info('4lza')
        {'Entity': {'@id': '1',
      '@type': 'protein',
      'Chain': [{'@id': 'A'}, {'@id': 'B'}]},
     'Method': {'@name': 'xray'},
     'bioAssemblies': '1',
     'release_date': 'Wed Aug 14 00:00:00 PDT 2013',
     'resolution': '1.84',
     'structureId': '4lza'}

    """
    out = get_info(pdb_id, url_root = 'http://www.rcsb.org/pdb/rest/getEntityInfo?structureId=')
    out = to_dict(out)
    return remove_at_sign( out['entityInfo']['PDB'] )

def describe_chemical(chem_id):
    """

    Parameters
    ----------

    chem_id : string
        A 4 character string representing the full chemical sequence of interest (ie, NAG)
    
    Returns
    -------

    out : dict
        A dictionary containing the chemical description associated with the PDB ID

    Examples
    --------
    >>> chem_desc = describe_chemical('NAG')
    >>> print(chem_desc)
    {'describeHet': {'ligandInfo': {'ligand': {'@molecularWeight': '221.208', 
    'InChIKey': 'OVRNDRQMDRJTHS-FMDGEEDCSA-N', '@type': 'D-saccharide', 
    'chemicalName': 'N-ACETYL-D-GLUCOSAMINE', '@chemicalID': 'NAG', 
    'smiles': 'CC(=O)N[C@@H]1[C@H]([C@@H]([C@H](O[C@H]1O)CO)O)O', '
    InChI': 'InChI=1S/C8H15NO6/c1-3(11)9-5-7(13)6(12)4(2-10)15-8(5)14/
    h4-8,10,12-14H,2H2,1H3,(H,9,11)/t4-,5-,6-,7-,8-/m1/s1', 
    'formula': 'C8 H15 N O6'}}}}

    """
    out = get_info(chem_id, url_root = 'http://www.rcsb.org/pdb/rest/describeHet?chemicalID=')
    out = to_dict(out)
    return out

def get_ligands(pdb_id):
    """Return ligands of given PDB ID

    Parameters
    ----------

    pdb_id : string
        A 4 character string giving a pdb entry of interest

    Returns
    -------

    out : dict
        A dictionary containing a list of ligands associated with the entry


    Examples
    --------
    >>> ligand_dict = get_ligands('100D')
    >>> print(ligand_dict)
    {'id': '100D',
    'ligandInfo': {'ligand': {'@chemicalID': 'SPM',
                           '@molecularWeight': '202.34',
                           '@structureId': '100D',
                           '@type': 'non-polymer',
                           'InChI': 'InChI=1S/C10H26N4/c11-5-3-9-13-7-1-2-8-14-10-4-6-12/h13-14H,1-12H2',
                           'InChIKey': 'PFNFFQXMRSDOHW-UHFFFAOYSA-N',
                           'chemicalName': 'SPERMINE',
                           'formula': 'C10 H26 N4',
                           'smiles': 'C(CCNCCCN)CNCCCN'}}}

    """
    out = get_info(pdb_id, url_root = 'http://www.rcsb.org/pdb/rest/ligandInfo?structureId=')
    out = to_dict(out)
    return remove_at_sign(out['structureId'])

def get_gene_onto(pdb_id):
    """Return ligands of given PDB_ID

    Parameters
    ----------

    pdb_id : string
        A 4 character string giving a pdb entry of interest

    Returns
    -------

    out : dict
        A dictionary containing the gene ontology information associated with the entry

    Examples
    --------

    >>> gene_info = get_gene_onto('4Z0L')
    >>> print(gene_info['term'][0])
    {'@chainId': 'A',
     '@id': 'GO:0001516',
     '@structureId': '4Z0L',
     'detail': {'@definition': 'The chemical reactions and pathways resulting '
                               'in the formation of prostaglandins, any of a '
                               'group of biologically active metabolites which '
                               'contain a cyclopentane ring.',
                '@name': 'prostaglandin biosynthetic process',
                '@ontology': 'B',
                '@synonyms': 'prostaglandin anabolism, prostaglandin '
                             'biosynthesis, prostaglandin formation, '
                             'prostaglandin synthesis'}}
    """
    out = get_info(pdb_id, url_root = 'http://www.rcsb.org/pdb/rest/goTerms?structureId=')
    out = to_dict(out)
    if not out['goTerms']:
        return None
    out = remove_at_sign(out['goTerms'])
    return out

def get_seq_cluster(pdb_id_chain):
    """Get the sequence cluster of a PDB ID plus a pdb_id plus a chain,

    Parameters
    ----------

    pdb_id_chain : string
        A string denoting a 4 character PDB ID plus a one character chain
        offset with a dot: XXXX.X, as in 2F5N.A

    Returns
    -------

    out : dict
        A dictionary containing the sequence cluster associated with the PDB 
        entry and chain

    Examples
    --------

    >>> sclust = get_seq_cluster('2F5N.A')
    >>> print(sclust['pdbChain'][:10])
    [{'@name': '4PD2.A', '@rank': '1'},
     {'@name': '3U6P.A', '@rank': '2'},
     {'@name': '4PCZ.A', '@rank': '3'},
     {'@name': '3GPU.A', '@rank': '4'},
     {'@name': '3JR5.A', '@rank': '5'},
     {'@name': '3SAU.A', '@rank': '6'},
     {'@name': '3GQ4.A', '@rank': '7'},
     {'@name': '1R2Z.A', '@rank': '8'},
     {'@name': '3U6E.A', '@rank': '9'},
     {'@name': '2XZF.A', '@rank': '10'}]

    """

    url_root = 'http://www.rcsb.org/pdb/rest/sequenceCluster?structureId='
    out = get_info(pdb_id_chain, url_root = url_root)
    out = to_dict(out)
    return remove_at_sign(out['sequenceCluster'])

def get_blast(pdb_id, chain_id='A'):
    """
    Return BLAST search results for a given PDB ID
    The key of the output dict())that outputs the full search results is 
    'BlastOutput_iterations'

    To get a list of just the results without the metadata of the search use:
    hits = full_results['BlastOutput_iterations']['Iteration']['Iteration_hits']['Hit']

    Parameters
    ----------
    pdb_id : string
        A 4 character string giving a pdb entry of interest

    chain_id : string
        A single character designating the chain ID of interest


    Returns
    -------
    
    out : dict()
        A nested dict() consisting of the BLAST search results and all associated metadata
        If you just want the hits, look under four levels of keys:
        results['BlastOutput_iterations']['Iteration']['Iteration_hits']['Hit']

    Examples
    --------

    >>> blast_results = get_blast('2F5N', chain_id='A')
    >>> just_hits = blast_results['BlastOutput_iterations']['Iteration']['Iteration_hits']['Hit']
    >>> print(just_hits[50]['Hit_hsps']['Hsp']['Hsp_hseq'])
    PELPEVETVRRELEKRIVGQKIISIEATYPRMVL--TGFEQLKKELTGKTIQGISRRGKYLIFEIGDDFRLISHLRMEGKYRLATLDAPREKHDHL
    TMKFADG-QLIYADVRKFGTWELISTDQVLPYFLKKKIGPEPTYEDFDEKLFREKLRKSTKKIKPYLLEQTLVAGLGNIYVDEVLWLAKIHPEKET
    NQLIESSIHLLHDSIIEILQKAIKLGGSSIRTY-SALGSTGKMQNELQVYGKTGEKCSRCGAEIQKIKVAGRGTHFCPVCQQ


    """

    raw_results = get_raw_blast(pdb_id, output_form='XML', chain_id=chain_id)

    out = xmltodict.parse(raw_results, process_namespaces=True)
    out = to_dict(out)
    out = out['BlastOutput']
    return out


def get_pfam(pdb_id):
    """Return PFAM annotations of given PDB_ID

    Parameters
    ----------

    pdb_id : string
        A 4 character string giving a pdb entry of interest

    Returns
    -------

    out : dict
        A dictionary containing the PFAM annotations for the specified PDB ID

    Examples
    --------

    >>> pfam_info = get_pfam('2LME')
    >>> print(pfam_info)
    {'pfamHit': {'@pfamAcc': 'PF03895.10', '@pfamName': 'YadA_anchor', 
    '@structureId': '2LME', '@pdbResNumEnd': '105', '@pdbResNumStart': '28', 
    '@pfamDesc': 'YadA-like C-terminal region', '@eValue': '5.0E-22', '@chainId': 'A'}}

    """
    out = get_info(pdb_id, url_root = 'http://www.rcsb.org/pdb/rest/hmmer?structureId=')
    out = to_dict(out)
    if not out['hmmer3']:
        return dict()
    return remove_at_sign(out['hmmer3'])

def get_clusters(pdb_id):
    """Return cluster related web services of given PDB_ID

    Parameters
    ----------

    pdb_id : string
        A 4 character string giving a pdb entry of interest

    Returns
    -------
    
    out : dict
        A dictionary containing the representative clusters for the specified PDB ID

    Examples
    --------

    >>> clusts = get_clusters('4hhb.A')
    >>> print(clusts)
    {'pdbChain': {'@name': '2W72.A'}}

    """
    out = get_info(pdb_id, url_root = 'http://www.rcsb.org/pdb/rest/representatives?structureId=')
    out = to_dict(out)
    return remove_at_sign(out['representatives'])

# Higher-level functions for searching


def find_results_gen(search_term, field='title'):
    '''
    Return a generator of the results returned by a search of
    the protein data bank. This generator
    
    Parameters
    ----------

    search_term : str
        The search keyword
        
    field : str
        The type of information to record about each entry

    Examples
    --------

    >>> result_gen = find_results_gen('bleb')
    >>> pprint.pprint([item for item in result_gen][:5])
    ['MYOSIN II DICTYOSTELIUM DISCOIDEUM MOTOR DOMAIN S456Y BOUND WITH MGADP-BEFX',
     'MYOSIN II DICTYOSTELIUM DISCOIDEUM MOTOR DOMAIN S456Y BOUND WITH MGADP-ALF4',
     'DICTYOSTELIUM DISCOIDEUM MYOSIN II MOTOR DOMAIN S456E WITH BOUND MGADP-BEFX',
     'MYOSIN II DICTYOSTELIUM DISCOIDEUM MOTOR DOMAIN S456E BOUND WITH MGADP-ALF4',
     'The structural basis of blebbistatin inhibition and specificity for myosin '
     'II']
        
    '''
    scan_params = make_query(search_term, querytype='AdvancedKeywordQuery')
    search_result_ids = do_search(scan_params)
    
    all_titles = []
    for pdb_result in search_result_ids:
        result= describe_pdb(pdb_result)
        if field in result.keys():
            yield result[field]
            
            
def find_papers(search_term, max_results=100):
    '''
    Return an ordered list of the top papers returned by a keyword search of
    the RCSB PDB
    
    Parameters
    ----------

    search_term : str
        The search keyword
        
    max_results : int
        The maximum number of results to return

    Returns
    -------

    all_papers : list of strings
        A descending-order list containing the top papers associated with
        the search term in the PDB

    Examples
    --------

    >>> matching_papers = find_papers('crispr',max_results=3)
    >>> print(matching_papers)
    ['Crystal structure of a CRISPR-associated protein from thermus thermophilus', 
    'CRYSTAL STRUCTURE OF HYPOTHETICAL PROTEIN SSO1404 FROM SULFOLOBUS SOLFATARICUS P2', 
    'NMR solution structure of a CRISPR repeat binding protein']
        
    '''
    
    papers = find_results_gen(search_term, field='title')
    all_papers = [paper for ind, paper in enumerate(papers) if ind < max_results]
    return remove_dupes(all_papers)

def find_authors(search_term, max_results=100):
    '''Return an ordered list of the top authors returned by a keyword search of
    the RCSB PDB

    This function is based on the number of unique PDB entries a given author has
    his or her name associated with, and not author order or the ranking of the 
    entry in the keyword search results. So if an author tends to publish on topics
    related to the search_term a lot, even if those papers are not the best match for 
    the exact search, he or she will have priority in this function over an author 
    who wrote the one paper that is most relevant to the search term. For the latter
    option, just do a standard keyword search using do_search.
    
    Parameters
    ----------

    search_term : str
        The search keyword
        
    max_results : int
        The maximum number of results to return

    Returns
    -------

    out : list of str


    Examples
    --------

    >>> top_authors = find_authors('crispr',max_results=100)
    >>> print(top_authors[:10])
    ['Doudna, J.A.', 'Jinek, M.', 'Ke, A.', 'Li, H.', 'Nam, K.H.']

    '''
    all_authors_raw = find_results_gen(search_term, field='citation_authors')
    all_individuals = [item for ind, item in enumerate(all_authors_raw) if ind < max_results]
    full_author_list = []
    for individual in all_individuals:
        individual = individual.replace('.,', '.;')
        author_list_clean = [x.strip() for x in individual.split(';')]
        full_author_list+=author_list_clean
    
    out = list(chain.from_iterable(repeat(ii, c) for ii,c in Counter(full_author_list).most_common()))


    return remove_dupes(out)

def find_dates(search_term, max_results=100):
    '''
    Return an ordered list of the PDB submission dates returned by a 
    keyword search of the RCSB PDB. This can be used to assess the
    popularity of a gievne keyword or topic
    
    Parameters
    ----------

    search_term : str
        The search keyword
        
    max_results : int
        The maximum number of results to return
        
    Returns
    -------

    all_dates : list of str
        A list of calendar strings associated with the search term, these can
        be converted directly into time or datetime objects

    '''
    
    dates = find_results_gen(search_term, field='deposition_date')
    all_dates = [date for ind, date in enumerate(dates) if ind < max_results]
    return all_dates



def list_taxa(pdb_list):
    '''Given a list of PDB IDs, look up their associated species
    
    This function digs through the search results returned
    by the get_all_info() function and returns any information on 
    taxonomy included within the description.

    The PDB website description of each entry includes the name 
    of the species (and sometimes details of organ or body part)
    for each protein structure sample. 

    Parameters
    ----------

    pdb_list : list of str
        List of PDB IDs

        
    Returns
    -------

    taxa : list of str
        A list of the names or classifictions of species 
        associated with entries

    Examples
    --------

    >>> crispr_query = make_query('crispr')
    >>> crispr_results = do_search(crispr_query)
    >>> print(list_taxa(crispr_results[:10]))
    ['Thermus thermophilus',
     'Sulfolobus solfataricus P2',
     'Hyperthermus butylicus DSM 5456',
     'unidentified phage',
     'Sulfolobus solfataricus P2',
     'Pseudomonas aeruginosa UCBPP-PA14',
     'Pseudomonas aeruginosa UCBPP-PA14',
     'Pseudomonas aeruginosa UCBPP-PA14',
     'Sulfolobus solfataricus',
     'Thermus thermophilus HB8']


    '''
    taxa = []
    for pdb_id in pdb_list:
        all_info = get_all_info(pdb_id)['polymer']
        if type(all_info)==list:
            if type(all_info[0]['Taxonomy'])==dict:
                taxa.append(all_info[0]['Taxonomy']['@name'])
            elif type(all_info[0]['Taxonomy'])==list:
                taxa.append(all_info[0]['Taxonomy'][0]['@name'])
        elif type(all_info)==dict:
            if type(all_info['Taxonomy'])==dict:
                taxa.append(all_info['Taxonomy']['@name'])
            elif type(all_info['Taxonomy'])==list:
                taxa.append(all_info['Taxonomy'][0]['@name'])
    return taxa


def list_types(pdb_list):
    '''Given a list of PDB IDs, look up their associated structure type
    

    Parameters
    ----------

    pdb_list : list of str
        List of PDB IDs

        
    Returns
    -------

    infotypes : list of str
        A list of the structure types associated with each PDB
        in the list. For many entries in the RCSB PDB, this defaults
        to 'protein'

    Examples
    --------

    >>> crispr_query = make_query('crispr')
    >>> crispr_results = do_search(crispr_query)
    >>> print(list_types(crispr_results[:5]))
    ['protein', 'protein', 'protein', 'protein', 'protein']
    '''
    infotypes = []
    for pdb_id in pdb_list:
        all_info = get_all_info(pdb_id)['polymer']
        if type(all_info)==list:
            infotypes.append(all_info[0]['@type'])
        elif type(all_info)==dict:
            infotypes.append(all_info['@type'])

    return infotypes


'''
=================
Helper Functions
=================
'''

def to_dict(odict):
    '''Convert OrderedDict to dict

    Takes a nested, OrderedDict() object and outputs a 
    normal dictionary of the lowest-level key:val pairs

    Parameters
    ----------
    
    odict : OrderedDict
    
    Returns
    -------

    out : dict

        A dictionary corresponding to the flattened form of 
        the input OrderedDict

    '''

    out = loads(dumps(odict))
    return out

def remove_at_sign(kk):
    '''Remove the '@' character from the beginning of key names in a dict()

    Parameters
    ----------

    kk : dict
        A dictionary containing keys with the @ character
        (this pops up a lot in converted XML)

    Returns
    -------

    kk : dict (modified in place)
        A dictionary where the @ character has been removed

    '''
    tagged_keys = [thing for thing in kk.keys() if thing.startswith('@')]
    for tag_key in tagged_keys:
        kk[tag_key[1:]] = kk.pop(tag_key)
        
    return kk

def remove_dupes(list_with_dupes):
    '''Remove duplicate entries from a list while preserving order

    This function uses Python's standard equivalence testing methods in
    order to determine if two elements of a list are identical. So if in the list [a,b,c]
    the condition a == b is True, then regardless of whether a and b are strings, ints, 
    or other, then b will be removed from the list: [a, c]

    Parameters
    ----------

    list_with_dupes : list
        A list containing duplicate elements

    Returns
    ------- 
    out : list
        The list with the duplicate entries removed by the order preserved


    Examples
    --------
    >>> a = [1,3,2,4,2]
    >>> print(remove_dupes(a))
    [1,3,2,4]

    '''
    visited = set()
    visited_add = visited.add
    out = [ entry for entry in list_with_dupes if not (entry in visited or visited_add(entry))]
    return out


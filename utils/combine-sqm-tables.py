#!/usr/bin/env python3

"""
Part of the SqueezeMeta distribution. 10/05/2021.
    (c) Fernando Puente-Sánchez, 2019-2020, CNB-CSIC / 2021 SLU.

Combine tabular outputs (as generated by sqm2tables.py or sqmreads2tables.py)
 from different SqueezeMeta or SQM_reads projects.

This script can combine the results of different samples ran using the 
 sequential mode, in which each sample is run separately, and also the
 results of different coassembly or merged SqueezeMeta runs.


USAGE:
usage: combine-sqm-tables.py [-h] PROJECT_PATHS
                             [-f PATHS_FILE]
                             [-o OUTPUT_DIR] [-p OUTPUT_PREFIX]
                             [--trusted-functions] [--ignore-unclassified]
                             [--sqm-reads] [--force-overwrite] [--doc]
                             project_paths [project_paths ...]

OPTIONS:
    -f/--paths-file: File containing the base paths of the SqueezeMeta projects
        to combine (one per line)
    -o/--output-dir: Name of the output directory (default: "combined")
    -p/--output-prefix: Prefix for the output files (default: "combined")
    --trusted-functions: Include only ORFs with highly trusted KEGG and
        COG assignments in aggregated functional tables
    --ignore-unclassified: Ignore ORFs without assigned functions in
        TPM calculation. Ignored if --sqm-reads is provided
    --sqm-reads: Projects were generated using sqm_reads.pl
    --force-overwrite: Write results even if the output directory
        already exists
    --doc: Show this documentation

EXAMPLES:
    # Combine projects /path/to/proj1 and /path/to/proj2,
    #  store results in "output_dir"
     combine-sqm-tables.py /path/to/proj1 /path/to/proj2 -o output_dir

    # Combine a list of projects contained in a file, use default output dir.
     combine-sqm-tables.py -f project_list.txt
"""

from os.path import abspath, dirname, realpath
from os import mkdir, listdir
from os.path import isfile, isdir
from sys import exit
import argparse
from subprocess import call

from pandas import DataFrame

from sys import path
utils_home = abspath(dirname(realpath(__file__)))
SQMpath = abspath('{}/../'.format(utils_home))

import warnings

def main(args):

    warnings.warn('combine-sqm-tables.py has been superseded by the `combineSQMlite` function of the `SQMtools` R package. Please consider using that instead')

    ### Check arguments.
    if args.paths_file:
        if args.project_paths:
            print('Project paths were provided directly as arguments and also in a file.')
            print('Using project paths in the file: "{}"'.format(args.paths_file))
        projPaths = [line.strip() for line in open(args.paths_file) if line.strip()]
    elif args.project_paths:
        projPaths = args.project_paths
    else:
        print('Project paths were not provided. Exiting...')
        exit(1)

    ### Create output dir.
    try:
       mkdir(args.output_dir)
    except OSError as e:
        if e.errno != 17:
            raise
        elif args.force_overwrite:
            pass
        else:
            print('\nThe directory {} already exists. Please remove it or use a different output name.\n'.format(args.output_dir))
            exit(1)

    ### Define stuff and things (Carl).
    sampleNames = []

    all_superkingdom = {}
    all_phylum = {}
    all_class = {}
    all_order = {}
    all_family = {}
    all_genus = {}
    all_species = {}

    prok_superkingdom = {}
    prok_phylum = {}
    prok_class = {}
    prok_order = {}
    prok_family = {}
    prok_genus = {}
    prok_species = {}

    no_superkingdom = {}
    no_phylum = {}
    no_class = {}
    no_order = {}
    no_family = {}
    no_genus = {}
    no_species = {}

    KOabund = {}
    KOcopy = {}
    KOtpm = {}

    COGabund = {}
    COGcopy = {}
    COGtpm = {}

    PFAMabund = {}
    PFAMcopy = {}
    PFAMtpm = {}

    customFunMethods = {}

    namesInfo = {}

    hasKEGG = True
    hasCOG = True
    hasPFAM = not args.sqmreads


    for projPath in projPaths:
        projName = projPath.strip('/').split('/')[-1]
        ### Validate projects.
        if not args.sqmreads:
            ok = isfile('{}/SqueezeMeta_conf.pl'.format(projPath))
        else:
            ok = isfile('{}/{}.out.mappingstat'.format(projPath, projName))
        if not ok:
            raise Exception('Path "{}" does not exist, or does not contain a valid SQM project'.format(projPath))

        ### Create tables if needed.
        if not isfile('{}/results/tables/{}.COG.abund.tsv'.format(projPath, projName)):
            print('Creating tables for project {}'.format(projName))
            if args.sqmreads and not isdir('{}/results'.format(projPath)):
                mkdir('{}/results'.format(projPath))
            if not args.sqmreads:
                command = ['{}/utils/sqm2tables.py'.format(SQMpath), '{}'.format(projPath), '{}/results/tables'.format(projPath)]
                if args.ignore_unclassified:
                    command.append('--ignore_unclassified')
            else:
                command = ['{}/utils/sqmreads2tables.py'.format(SQMpath), '{}'.format(projPath), '{}/results/tables'.format(projPath)]
            if args.trusted_functions:
                command.append('--trusted-functions')
            command.append('--force-overwrite')
            call(command)
        else:
            print('The "{}/results/tables" directory is already present. Skipping...'.format(projPath))

        ### Is there any custom annotation method?
        custom_thissample = {}
        for f in listdir('{}/results/tables/'.format(projPath)):
            fields = f.split('.')
            method = fields[-3]
            counts = fields[-2]
            if counts in ('abund', 'tpm', 'copyNumber') and method not in ('KO', 'COG', 'PFAM', 'allfilter', 'prokfilter', 'nofilter', 'orf', 'contig'):
                if method not in custom_thissample:
                    custom_thissample[method] = {}
                custom_thissample[method][counts] = f
                if method not in customFunMethods:
                    customFunMethods[method] = {}
                if counts not in customFunMethods[method]:
                    customFunMethods[method][counts] = {}

        ### Parse tables.
        samples = parse_table('{}/results/tables/{}.superkingdom.allfilter.abund.tsv'.format(projPath, projName), all_superkingdom)
        sampleNames.extend(samples)

        parse_table('{}/results/tables/{}.phylum.allfilter.abund.tsv'.format(projPath, projName), all_phylum)
        parse_table('{}/results/tables/{}.class.allfilter.abund.tsv'.format(projPath, projName), all_class)
        parse_table('{}/results/tables/{}.order.allfilter.abund.tsv'.format(projPath, projName), all_order)
        parse_table('{}/results/tables/{}.family.allfilter.abund.tsv'.format(projPath, projName), all_family)
        parse_table('{}/results/tables/{}.genus.allfilter.abund.tsv'.format(projPath, projName), all_genus)
        parse_table('{}/results/tables/{}.species.allfilter.abund.tsv'.format(projPath, projName), all_species)

        parse_table('{}/results/tables/{}.superkingdom.prokfilter.abund.tsv'.format(projPath, projName), prok_superkingdom)
        parse_table('{}/results/tables/{}.phylum.prokfilter.abund.tsv'.format(projPath, projName), prok_phylum)
        parse_table('{}/results/tables/{}.class.prokfilter.abund.tsv'.format(projPath, projName), prok_class)
        parse_table('{}/results/tables/{}.order.prokfilter.abund.tsv'.format(projPath, projName), prok_order)
        parse_table('{}/results/tables/{}.family.prokfilter.abund.tsv'.format(projPath, projName), prok_family)
        parse_table('{}/results/tables/{}.genus.prokfilter.abund.tsv'.format(projPath, projName), prok_genus)
        parse_table('{}/results/tables/{}.species.prokfilter.abund.tsv'.format(projPath, projName), prok_species)

        parse_table('{}/results/tables/{}.superkingdom.nofilter.abund.tsv'.format(projPath, projName), no_superkingdom)
        parse_table('{}/results/tables/{}.phylum.nofilter.abund.tsv'.format(projPath, projName), no_phylum)
        parse_table('{}/results/tables/{}.class.nofilter.abund.tsv'.format(projPath, projName), no_class)
        parse_table('{}/results/tables/{}.order.nofilter.abund.tsv'.format(projPath, projName), no_order)
        parse_table('{}/results/tables/{}.family.nofilter.abund.tsv'.format(projPath, projName), no_family)
        parse_table('{}/results/tables/{}.genus.nofilter.abund.tsv'.format(projPath, projName), no_genus)
        parse_table('{}/results/tables/{}.species.nofilter.abund.tsv'.format(projPath, projName), no_species)
        
        if not isfile('{}/results/tables/{}.KO.abund.tsv'.format(projPath, projName)): # assuming sqm2tables and sqmreads2tables properly handle projects with the nokegg/nocog/nopfam flags.
            print('Project at {}/{} is missing KEGG annotations, so they will be not included in the combined tables'.format(projPath, projName))
            hasKEGG = False
        else:
            parse_table('{}/results/tables/{}.KO.abund.tsv'.format(projPath, projName), KOabund)
            if not args.sqmreads:
                parse_table('{}/results/tables/{}.KO.copyNumber.tsv'.format(projPath, projName), KOcopy)
                parse_table('{}/results/tables/{}.KO.tpm.tsv'.format(projPath, projName), KOtpm)


        if not isfile('{}/results/tables/{}.COG.abund.tsv'.format(projPath, projName)):
            print('Project at {}/{} is missing COG annotations, so they will be not included in the combined tables'.format(projPath, projName))
            hasCOG = False
        else:
            parse_table('{}/results/tables/{}.COG.abund.tsv'.format(projPath, projName), COGabund)
            if not args.sqmreads:
                parse_table('{}/results/tables/{}.COG.copyNumber.tsv'.format(projPath, projName), COGcopy)
                parse_table('{}/results/tables/{}.COG.tpm.tsv'.format(projPath, projName), COGtpm)


        if not args.sqmreads:
            if not isfile('{}/results/tables/{}.PFAM.abund.tsv'.format(projPath, projName)):
                print('Project at {}/{} is missing PFAM annotations, so they will be not included in the combined tables'.format(projPath, projName))
                hasPFAM = False
            else:
                parse_table('{}/results/tables/{}.PFAM.abund.tsv'.format(projPath, projName), PFAMabund)
                parse_table('{}/results/tables/{}.PFAM.copyNumber.tsv'.format(projPath, projName), PFAMcopy)
                parse_table('{}/results/tables/{}.PFAM.tpm.tsv'.format(projPath, projName), PFAMtpm)

        for method in custom_thissample: # Add custom annotation methods!
            for counts, f in custom_thissample[method].items():
                parse_table('{}/results/tables/{}'.format(projPath, f), customFunMethods[method][counts])

        # Add function names and hierarchy paths.
        allMethods = []
        if hasKEGG: allMethods.append('KO')
        if hasCOG:  allMethods.append('COG')
        allMethods.extend(customFunMethods.keys())
        for method in allMethods:
            if method not in namesInfo:
                namesInfo[method] = {'Name': {}, 'Path': {}} if method in ('KO', 'COG') else {'Name': {}}
            with open('{}/results/tables/{}.{}.names.tsv'.format(projPath, projName, method)) as infile:
                infile.readline() # Burn headers
                for line in infile:
                    line = line.strip('\n').split('\t') # Explicitly strip just '\n' so I don't remove tabs when there are empty fields.
                    namesInfo[method]['Name'][line[0]] = line[1]
                    if 'Path' in namesInfo[method]:
                        namesInfo[method]['Path'][line[0]] = line[2]
                

        

    ### Write combined tables.
    prefix = '{}/{}.'.format(args.output_dir, args.output_prefix)

    write_feature_dict(sampleNames, all_superkingdom, prefix + 'superkingdom.allfilter.abund.tsv')
    write_feature_dict(sampleNames, all_phylum, prefix + 'phylum.allfilter.abund.tsv')
    write_feature_dict(sampleNames, all_class, prefix + 'class.allfilter.abund.tsv')
    write_feature_dict(sampleNames, all_order, prefix + 'order.allfilter.abund.tsv')
    write_feature_dict(sampleNames, all_family, prefix + 'family.allfilter.abund.tsv')
    write_feature_dict(sampleNames, all_genus, prefix + 'genus.allfilter.abund.tsv')
    write_feature_dict(sampleNames, all_species, prefix + 'species.allfilter.abund.tsv')

    write_feature_dict(sampleNames, prok_superkingdom, prefix + 'superkingdom.prokfilter.abund.tsv')
    write_feature_dict(sampleNames, prok_phylum, prefix + 'phylum.prokfilter.abund.tsv')
    write_feature_dict(sampleNames, prok_class, prefix + 'class.prokfilter.abund.tsv')
    write_feature_dict(sampleNames, prok_order, prefix + 'order.prokfilter.abund.tsv')
    write_feature_dict(sampleNames, prok_family, prefix + 'family.prokfilter.abund.tsv')
    write_feature_dict(sampleNames, prok_genus, prefix + 'genus.prokfilter.abund.tsv')
    write_feature_dict(sampleNames, prok_species, prefix + 'species.prokfilter.abund.tsv')

    write_feature_dict(sampleNames, no_superkingdom, prefix + 'superkingdom.nofilter.abund.tsv')
    write_feature_dict(sampleNames, no_phylum, prefix + 'phylum.nofilter.abund.tsv')
    write_feature_dict(sampleNames, no_class, prefix + 'class.nofilter.abund.tsv')
    write_feature_dict(sampleNames, no_order, prefix + 'order.nofilter.abund.tsv')
    write_feature_dict(sampleNames, no_family, prefix + 'family.nofilter.abund.tsv')
    write_feature_dict(sampleNames, no_genus, prefix + 'genus.nofilter.abund.tsv')
    write_feature_dict(sampleNames, no_species, prefix + 'species.nofilter.abund.tsv')

    if hasKEGG:
        write_feature_dict(sampleNames, KOabund, prefix + 'KO.abund.tsv')
        if not args.sqmreads: 
            write_feature_dict(sampleNames, KOcopy, prefix + 'KO.copyNumber.tsv')
            write_feature_dict(sampleNames, KOtpm, prefix + 'KO.tpm.tsv')

    if hasCOG:
        write_feature_dict(sampleNames, COGabund, prefix + 'COG.abund.tsv')
        if not args.sqmreads:
            write_feature_dict(sampleNames, COGcopy, prefix + 'COG.copyNumber.tsv')
            write_feature_dict(sampleNames, COGtpm, prefix + 'COG.tpm.tsv')

    if not args.sqmreads and hasPFAM:
        write_feature_dict(sampleNames, PFAMabund, prefix + 'PFAM.abund.tsv')
        write_feature_dict(sampleNames, PFAMcopy, prefix + 'PFAM.copyNumber.tsv')
        write_feature_dict(sampleNames, PFAMtpm, prefix + 'PFAM.tpm.tsv')

    for method in customFunMethods: # Write custom annotation methods!
        for counts, d in customFunMethods[method].items():
            custom_sampleNames = [s for s in sampleNames if s in d] # Define dinamically since we're not fully sure that all projects used the same methods.
            write_feature_dict(custom_sampleNames, d, prefix + '{}.{}.tsv'.format(method, counts))


    # Combine function names and hierarchy paths.
    allMethods = []
    if hasKEGG: allMethods.append('KO')
    if hasCOG:  allMethods.append('COG')
    allMethods.extend(customFunMethods.keys())
    for method in allMethods:
        columns = ['Name', 'Path'] if method in ('KO', 'COG') else ['Name']
        write_feature_dict(columns, namesInfo[method], prefix + method + '.names.tsv') 
    




def parse_table(path, targetDict):
    """
    Inserts a set of samples from a table in a dictionary.
    The dictionary is modified in place.
    Returns a list with the names of the samples.
    """
    with open(path) as infile:
        samples = infile.readline().strip().split('\t')
        for sample in samples:
            if sample in targetDict:
                raise Exception('Error where parsing table in "{}". Sample "{}" appears more than once in your input tables.'.format(path, sample))
            targetDict[sample] = {}
        for line in infile:
            line = line.strip().split('\t')
            feature = line[0]
            for sample, value in zip(samples, line[1:]):
                targetDict[sample][feature] = value
        return samples


def write_feature_dict(sampleNames, featureDict, outName):
    df = DataFrame.from_dict(featureDict).fillna(0)
    df = df.sort_index()
    df = df[sampleNames]
    df.to_csv(outName, sep='\t')



def parse_args():
    parser = argparse.ArgumentParser(description='Aggregate SqueezeMeta results into tables', epilog='Fernando Puente-Sánchez (CNB-SLU) 2021\n')
    parser.add_argument('project_paths', type=str, nargs='*', help='Base paths of the SqueezeMeta projects to combine')
    parser.add_argument('-f', '--paths-file', type=str, help='File containing the base paths of the SqueezeMeta projects to combine (one per line)')
    parser.add_argument('-o', '--output-dir', type=str, default='combined', help='Output directory')
    parser.add_argument('-p', '--output-prefix', type=str, default='combined', help='Prefix for output files')
    parser.add_argument('--trusted-functions', action='store_true', help='Include only ORFs with highly trusted KEGG and COG assignments in aggregated functional tables')
    parser.add_argument('--ignore-unclassified', action='store_true', help='Ignore ORFs without assigned functions in TPM calculation')
    parser.add_argument('--sqmreads', action='store_true', help='Projects were generated using sqm_reads.pl')
    parser.add_argument('--force-overwrite', action='store_true', help='Write results even if the output directory already exists')
    parser.add_argument('--doc', action='store_true', help='Show documentation')

    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    if args.doc:
        print(__doc__)
    else:
        main(args)

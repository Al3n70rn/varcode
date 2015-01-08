from reference_name import infer_reference_name
from variant import Variant
import maf

import vcf

def flatten_info_dictionary(info):
    """
    The INFO field of a VCF file is represented as a mapping between a key
    and a list of values for each sample. Since we're only concerned
    with the single-sample case, we flatten this k->list mapping into a
    simpler k->v mapping by extracting the first element of each list.
    """
    result = {}
    for (k,v) in info.iteritems():
        assert len(v) == 1, \
            "Expected INFO values to have length 1, got %s with %d elements" % (
                v, len(v))
        result[k] = v[0]
    return result

class VariantCollection(object):

    def _init_from_vcf(self, filename):
        """
        Construct contents of this object by parsing the given VCF filename.

        Drop any entries whose FILTER field is not one of "." or "PASS".

        After calling this method, the fields self.raw_reference_name and
        self.records will be initialized.
        """

        vcf_reader = vcf.Reader(filename=filename)
        self.raw_reference_name = vcf_reader.metadata['reference']

        self.records = [
            Variant(
                x.CHROM, x.POS,
                x.REF, x.ALT[0].sequence,
                flatten_info_dictionary(x.INFO))
            for x in vcf_reader
            if x.FILTER is None or x.FILTER == "PASS"
        ]

    def _init_from_maf(self, filename):
        """
        Construct contents of this object by parsing the given MAF filename.

        After calling this method, the fields self.raw_reference_name and
        self.records will be initialized.
        """
        maf_df = maf.load_maf_dataframe(filename)

        if len(maf_df) == 0:
            raise ValueError("Empty MAF file %s" % filename)

        ncbi_builds = maf_df.NCBI_Build.unique()

        if len(ncbi_builds) == 0:
            raise ValueError("No NCBI builds for MAF file %s" % filename)
        elif len(ncbi_builds) > 1:
            raise ValueError(
                "Multiple NCBI builds (%s) for MAF file %s" % (ncbi_builds, filename))

        self.raw_reference_name = ncbi_builds[0]
        self.records = []
        for _, x in maf_df.iterrows():
            start_pos = x.Start_Position
            end_pos = x.End_Position
            contig = x.Chromosome
            ref = normalize_nucleotide_string(x.Reference_Allele)

            if x.Tumor_Seq_Allele1 != ref:
                alt = x.Tumor_Seq_Allele1
            else:
                assert x.Tumor_Seq_Allele2 != ref, \
                    "Both tumor alleles agree with reference: %s" % (x,)
                alt = x.Tumor_Seq_Allele2

            alt = normalize_nucleotide_string(alt)

            record = Variant(contig, start_pos, ref, alt)
            self.records.append(record)

    def __init__(self, filename):
        assert isinstance(filename, (str,unicode)), \
            "Expected filename to be str, got %s : %s" % (
                filename, type(filename))

        if filename.endswith(".vcf"):
            self._init_from_vcf(filename)
        elif filename.endswith(".maf"):
            self._init_from_maf(filename)
        else:
            raise ValueErrr("Unrecognized file type: %s" % filename)

        self.reference_name = infer_reference_name(self.raw_reference_name)

    def __len__(self):
        return len(self.records)

    def __iter__(self):
        return iter(self.records)
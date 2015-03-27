# Copyright (c) 2015. Mount Sinai School of Medicine
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Effect annotation for variants which modify the coding sequence and change
reading frame.
"""

from .effects import FrameShift, FrameShiftTruncation
from .translate import translate

def _frameshift_inside_cds(
        codon_index_before_mutation,
        coding_sequence_after_mutation,
        variant,
        transcript):
    """
    Determine frameshift effect when mutation applies after start
    codon and before stop codon.

    Parameters
    ----------
    codon_index_before_mutation : int
    coding_sequence_after_mutation: Bio.Seq
    variant : Variant
    transcript : transcript
    """
    assert transcript.protein_sequence is not None, \
        "Expect transcript %s to have protein sequence" % transcript

    # codon offset (starting from 0 = start codon) of first non-reference
    # amino acid in the variant protein
    mutation_codon_offset = codon_index_before_mutation + 1

    assert mutation_codon_offset > 0, \
        "Expected mutation %s to be after start codon of %s (offset = %d)" % (
            variant, transcript, mutation_codon_offset)

    stop_codon_offset = len(transcript.protein_sequence)
    assert mutation_codon_offset < stop_codon_offset, \
        ("Expected mutation %s to be before"
         " stop codon of %s (offset = %d, stop codon at %d)") % (
         variant,
         transcript,
         mutation_codon_offset,
         stop_codon_offset)

    protein_before_mutation = \
        transcript.protein_sequence[:mutation_codon_offset]

    protein_after_insertion = translate(
        nucleotide_sequence=coding_sequence_after_mutation,
        first_codon_is_start=False,
        to_stop=True)

    if len(protein_after_insertion) == 0:
        # if a frameshift doesn't create any new amino acids, then
        # it must immediately have hit a stop codon
        return FrameShiftTruncation(
            variant=variant,
            transcript=transcript,
            aa_pos=mutation_codon_offset,
            aa_ref=protein_before_mutation[-1])
    return FrameShift(
        variant=variant,
        transcript=transcript,
        aa_pos=mutation_codon_offset,
        aa_ref=protein_before_mutation[-1],
        shifted_sequence=protein_after_insertion)

def frameshift_coding_insertion_effect(
        cds_offset_before_insertion,
        inserted_nucleotides,
        sequence_from_start_codon,
        variant,
        transcript):
    """
    Assumption:
        The insertion is happening after the start codon and before the stop
        codon of this coding sequence.
    """

    if cds_offset_before_insertion % 3 == 2:
        # if insertion happens after last nucleotide in a codons
        codon_index_before_insertion = int(cds_offset_before_insertion / 3)
    else:
        # if insertion happens after the 1st or 2nd nucleotide in a codon,
        # then it disrupts that codon
        codon_index_before_insertion = int(cds_offset_before_insertion / 3) - 1

    assert codon_index_before_insertion >= 0, \
        "Expected frameshift_insertion to be after start codon for %s on %s" % (
            variant, transcript)

    original_protein_sequence = transcript.protein_sequence

    assert codon_index_before_insertion < len(original_protein_sequence) - 1, \
        "Expected frameshift_insertion to be before stop codon for %s on %s" % (
            variant, transcript)

    if codon_index_before_insertion == len(original_protein_sequence) - 1:
        # if insertion is into the stop codon then this is a stop-loss
        pass

    cds_offset_after_insertion = (codon_index_before_insertion + 1) * 3
    original_coding_sequence_after_insertion = \
        sequence_from_start_codon[cds_offset_after_insertion:]
    coding_sequence_after_insertion = \
        inserted_nucleotides + original_coding_sequence_after_insertion

    mutation_codon_offset = codon_index_before_insertion + 1
    protein_before_mutation = original_protein_sequence[:mutation_codon_offset]
    return _frameshift_inside_cds(
        protein_before_mutation=protein_before_mutation,
        coding_sequence_after_mutation=coding_sequence_after_insertion,
        variant=variant,
        transcript=transcript)

def frameshift_coding_effect(
        ref,
        alt,
        cds_offset,
        sequence_from_start_codon,
        variant,
        transcript):

    if len(ref) == 0:
        return frameshift_coding_insertion_effect(
            cds_offset_before_insertion=cds_offset,
            inserted_nucleotides=alt,
            sequence_from_start_codon=sequence_from_start_codon,
            variant=variant,
            transcript=transcript)

    assert len(alt) > 0, \
         "Expected len(alt) > 0 in frameshift_coding_effect for %s on %s" % (
            variant, transcript)


    original_protein_sequence = transcript.protein_sequence

    mutated_codon_index = int(cds_offset / 3)

    protein_before_mutation = original_protein_sequence[:mutated_codon_index]
    sequence_after_mutation = sequence_from_start_codon[cds_offset:]

    variant_sequence = substitute(
        sequence_after_mutation,
        ref,
        alt)


from __future__ import print_function, division, absolute_import

import Bio.Seq
from memoized_property import memoized_property

class TranscriptMutationEffect(object):

    def __init__(self, variant, transcript):
        self.variant = variant
        self.transcript = transcript

    def __repr__(self):
        return str(self)

    def __str__(self):
        return "%s(variant=%s, transcript=%s)" % (
            self.__class__.__name__,
            self.variant.short_description(),
            self.transcript.name)

    def short_description():
        raise ValueError(
            "Method short_description() not implemented for %s" % self)

    is_coding = False

    @memoized_property
    def original_nucleotide_sequence(self):
        return self.transcript.coding_sequence

    @memoized_property
    def original_protein_sequence(self):
        return Bio.Seq.translate(
            str(self.original_nucleotide_sequence),
            to_stop=True,
            cds=True)

    @memoized_property
    def mutant_protein_sequence(self):
        raise ValueError(
            "mutant_protein_sequence not implemented for %s" % (
                self.__class__.__name__,))

class NoncodingTranscript(TranscriptMutationEffect):
    """
    Any mutation to a transcript with a non-coding biotype
    """
    def short_description(self):
        return "non-coding-transcript"

class IncompleteTranscript(TranscriptMutationEffect):
    """
    Any mutation to an incompletely annotated transcript with a coding biotype
    """
    def short_description(self):
        return "incomplete"

class FivePrimeUTR(TranscriptMutationEffect):
    """
    Any mutation to the 5' untranslated region (before the start codon) of
    coding transcript.
    """
    def short_description(self):
        return "5' UTR"

class ThreePrimeUTR(TranscriptMutationEffect):
    """
    Any mutation to the 3' untranslated region (after the stop codon) of
    coding transcript.
    """
    def short_description(self):
        return "3' UTR"


class Intronic(TranscriptMutationEffect):
    """
    Mutation in an intronic region of a coding transcript
    """
    def __init__(self, variant, transcript, nearest_exon, distance_to_exon):
        TranscriptMutationEffect.__init__(self, variant, transcript)
        self.nearest_exon = nearest_exon
        self.distance_to_exon = distance_to_exon

    def short_description(self):
        return "intronic"

class SpliceSite(object):
    """
    Parent class for all splice site mutations.
    """
    pass

class IntronicSpliceSite(Intronic, SpliceSite):
    """
    Mutations near exon boundaries, excluding the first two and last two
    nucleotides in an intron, since those are  known to more confidently
    affect splicing and are given their own effect classes below.
    """
    def __init__(self, *args, **kwargs):
        Intronic.__init__(self, *self, **kwargs)

    def short_description(self):
        return "intronic-splice-site"

class SpliceDonor(IntronicSpliceSite):
    """
    Mutation in the first two intron residues.
    """
    def __init__(self, *args, **kwargs):
        Intronic.__init__(self, *self, **kwargs)

    def short_description(self):
        return "splice-donor"

class SpliceAcceptor(IntronicSpliceSite):
    """
    Mutation in the last two intron residues.
    """
    def short_description(self):
        return "splice-acceptor"

class Exonic(TranscriptMutationEffect):
    """
    Any mutation which affects the contents of an exon (coding region or UTRs)
    """
    pass

class ExonicSpliceSite(Exonic, SpliceSite):
    """
    Mutation in the last three nucleotides before an intron
    or in the first nucleotide after an intron.
    """
    def short_description(self):
        return "exonic-splice-site"

class CodingMutation(Exonic):
    """
    Base class for all mutations which result in a modified coding sequence.
    """
    def __init__(self, variant, transcript, aa_pos, aa_ref):
        """
        Parameters
        ----------
        variant : varcode.Variant

        transcript : pyensembl.Transcript

        aa_pos : int
            Position of first modified amino aicd (starting from 0)

        aa_ref : str
            Amino acid string of what used to be at aa_pos in the
            wildtype (unmutated) protein.
        """
        Exonic.__init__(self, variant, transcript)
        self.aa_pos = aa_pos
        self.aa_ref = aa_ref

    def __str__(self):
        return "%s(variant=%s, transcript=%s, effect_description=%s)" % (
            self.__class__.__name__,
            self.variant.short_description(),
            self.transcript.name,
            self.short_description())

    is_coding = True


class Silent(CodingMutation):
    """
    Mutation to an exon of a coding region which doesn't change the
    amino acid sequence.
    """
    def short_description(self):
        return "silent"


class BaseSubstitution(CodingMutation):
    """
    Coding mutation which replaces some amino acids into others.
    The total number of amino acids changed must be greater than one on
    either the reference or alternate.
    """
    def __init__(
            self,
            variant,
            transcript,
            aa_pos,
            aa_ref,
            aa_alt):

        CodingMutation.__init__(
            self,
            variant=variant,
            transcript=transcript,
            aa_pos=aa_pos,
            aa_ref=aa_ref)

        self.aa_alt = aa_alt
        self.mutation_start = aa_pos
        self.mutation_end = aa_pos + len(aa_alt)

    def short_description(self):
        if len(self.aa_ref) == 0:
            return "p.%dins%s" % (self.aa_pos, self.aa_alt)
        elif len(self.aa_alt) == 0:
            return "p.%s%ddel" % (self.aa_ref, self.aa_pos)
        else:
            return "p.%s%d%s" % (
                    self.aa_ref,
                    self.aa_pos + 1,
                    self.aa_alt)

    @memoized_property
    def mutant_protein_sequence(self):
        original = self.original_protein_sequence
        prefix = original[:self.aa_pos]
        suffix = original[self.aa_pos + len(self.aa_ref):]
        return prefix + self.aa_alt + suffix

class Substitution(BaseSubstitution):
    """
    Single amino acid subsitution, e.g. BRAF-001 V600E
    """
    def __init__(
            self,
            variant,
            transcript,
            aa_pos,
            aa_ref,
            aa_alt):
        if len(aa_ref) != 1:
            raise ValueError(
                "Simple subsitution can't have aa_ref='%s'" % (aa_ref,))
        if len(aa_alt) != 1:
            raise ValueError(
                "Simple subsitution can't have aa_alt='%s'" % (aa_alt,))
        BaseSubstitution.__init__(
            self,
            variant=variant,
            transcript=transcript,
            aa_pos=aa_pos,
            aa_ref=aa_ref,
            aa_alt=aa_alt)

class ComplexSubstitution(BaseSubstitution):
    """
    In-frame substitution of multiple amino acids, e.g. TP53-002 p.391FY>QQQ
    Can change the length of the protein sequence but since it has
    non-empty ref and alt strings, is more complicated than an insertion or
    deletion alone.
    """
    def __init__(
            self,
            variant,
            transcript,
            aa_pos,
            aa_ref,
            aa_alt):
        if len(aa_ref) == 1 and len(aa_alt) == 1:
            raise ValueError(
                "ComplexSubstitution can't have aa_ref='%s' and aa_alt='%s'" % (
                    aa_ref, aa_alt))
        BaseSubstitution.__init__(
            self,
            variant=variant,
            transcript=transcript,
            aa_pos=aa_pos,
            aa_ref=aa_ref,
            aa_alt=aa_alt)

class Insertion(BaseSubstitution):
    """
    In-frame insertion of one or more amino acids.
    """
    def __init__(self, variant, transcript, aa_pos, aa_alt):
        BaseSubstitution.__init__(
            self,
            variant=variant,
            transcript=transcript,
            aa_pos=aa_pos,
            aa_ref="",
            aa_alt=aa_alt)

class Deletion(BaseSubstitution):
    """
    In-frame deletion of one or more amino acids.
    """

    def __init__(self, variant, transcript, aa_pos, aa_ref):
        BaseSubstitution.__init__(
            self,
            variant=variant,
            transcript=transcript,
            aa_pos=aa_pos,
            aa_ref=aa_ref,
            aa_alt="")



class PrematureStop(BaseSubstitution):
    def __init__(
            self,
            variant,
            transcript,
            aa_pos,
            aa_ref):
        BaseSubstitution.__init__(
            self,
            variant,
            transcript,
            aa_pos=aa_pos,
            aa_ref=aa_ref,
            aa_alt="*")

    def short_description(self):
        return "p.%s%d*" % (
            self.aa_ref,
            self.aa_pos + 1)

    @memoized_property
    def mutant_protein_sequence(self):
        return self.original_protein_sequence[:self.aa_pos]


class UnpredictableCodingMutation(BaseSubstitution):
    """
    Variants for which we can't confidently determine a protein sequence.

    Splice site mutations are unpredictable since they require a model of
    alternative splicing that goes beyond this library. Similarly,
    when a start codon is lost it's difficult to determine if there is
    an alternative Kozak consensus sequence (either before or after the
    original) from which an alternative start codon can be inferred.
    """

    @property
    def mutant_protein_sequence(self):
        raise ValueError("Can't determine the protein sequence of %s" % self)

class StopLoss(UnpredictableCodingMutation):
    def short_description(self):
        return "*%d%s (stop-loss)" % (self.aa_pos, self.aa_alt)

class StartLoss(UnpredictableCodingMutation):
    def __init__(
            self,
            variant,
            transcript,
            aa_pos,
            aa_alt):
        UnpredictableCodingMutation.__init__(
            self,
            variant,
            transcript,
            aa_pos=aa_pos,
            aa_ref="M",
            aa_alt=aa_alt)

    def short_description(self):
        return "p.? (start-loss)" % (self.aa_pos, self.aa_)

class FrameShift(CodingMutation):
    def __init__(
            self,
            variant,
            transcript,
            aa_pos,
            aa_ref,
            shifted_sequence):
        """
        Unlike an insertion, which we denote with aa_ref as the chracter before
        the variant sequence, a frameshift starts at aa_ref
        """
        CodingMutation.__init__(
            self,
            variant=variant,
            transcript=transcript,
            aa_pos=aa_pos,
            aa_ref=aa_ref)
        self.shifted_sequence = shifted_sequence
        self.mutation_start = self.aa_pos
        self.mutation_end = self.aa_pos + len(shifted_sequence)

    @memoized_property
    def mutant_protein_sequence(self):
        original_aa_sequence = self.original_protein_sequence[:self.aa_pos]
        return original_aa_sequence + self.shifted_sequence

    def short_description(self):
        return "p.%s%dfs" % (self.aa_ref, self.aa_pos + 1)

class FrameShiftTruncation(PrematureStop, FrameShift):
    """
    A frame-shift mutation which immediately introduces a stop codon.
    """
    def __init__(self, *args, **kwargs):
        super(PrematureStop, self).__init__(*args, **kwargs)

    @memoized_property
    def mutant_protein_sequence(self):
        return self.original_protein_sequence[:self.aa_pos]

    def short_description(self):
        return "p.%s%dfs*" % (self.aa_ref, self.aa_pos + 1)
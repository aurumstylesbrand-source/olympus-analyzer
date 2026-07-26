1:

Shipd
/
olympus
Home
Events
Submissions
Payouts

587/600
2
Silver
Create
· $150–350
61
Verifier Completeness Audit
Structural diff between two PDF documents

Back to submission
Task description


lopdf can load two PDFs, but there is no way to compare them structurally. Raw Object equality is not enough here, because two independently loaded files use different object ids for the same logical content. Build a real structural diff, where two documents holding the same content produce no changes at all.

Add Document::diff(&self, other: &Document) -> DocumentDiff and Document::diff_with(&self, other: &Document, options: DiffOptions) -> DocumentDiff. DocumentDiff has a public field changes: Vec<Change> plus the methods is_empty(), len(), iter(), contains_path(&str), render() -> String, summary() -> DiffSummary, changed_page_numbers(), changes_for_page(usize), and structural_changes(). Each Change has public fields path: String and kind: ChangeKind. DiffOptions::default() compares everything, and its without_metadata(), without_annotations(), and without_structure() each return a copy with that scope switched off. DiffSummary has public count fields pages_added, pages_removed, pages_moved, and pages_modified, and a total() method equal to the number of changes. The new types Change, ChangeKind, DiffOptions, DiffSummary, and DocumentDiff are re-exported at the crate root and derive Debug.

Resolve indirect references before comparing, so identical content under different ids diffs as empty, and handle cycles in the object graph so the comparison always terminates. For dictionaries, report added, removed, modified, and type-changed entries: a key on one side only is Added or Removed; a changed value is Modified; a changed object type is TypeChanged. Arrays of different length are LengthChanged, and a stream is StreamContentChanged when its decoded bytes differ.

Pages are matched by content, not position. A page inserted in the middle is a single PageAdded, not a cascade on every later page; a dropped page is PageRemoved; a page whose content moved to a new index is PageMoved; a page kept in place but edited surfaces a PageModified marker alongside the field-level changes recorded under that page. Because attributes such as MediaBox, Resources, and Rotate may be inherited from an ancestor, resolve each page's effective value first, so inline in one file and inherited in the other is not a difference.

Annotations on a page are compared order-insensitively, reporting AnnotationAdded, AnnotationRemoved, and AnnotationChanged. Structure is compared too: catalog entries such as page layout, the outline tree (OutlineAdded, OutlineRemoved, or OutlineChanged when an outline points to a different page), and the trailer document id. An outline's destination is compared by the page it targets, so differing object ids alone are not a change. Info metadata is compared as well. With a scope switched off through DiffOptions, none of its changes appear.

Every change carries a readable path: a page-level change is page 2, a field on a page is page 2/Contents, a catalog field is catalog/PageLayout, metadata is Info/Title, and the trailer id is under trailer/ID. changes_for_page returns only the changes recorded under one page and structural_changes only those outside any page, while changed_page_numbers lists every page number that carries a change. The summary exposes the page add, remove, move, and modify counts, and total() matches the number of recorded changes, while render() prints one line per change.
Incomplete
11 demonstrated
The audit demonstrated 11 gaps where a broken implementation could still pass the current tests. Review the proposed test patch below.

Completed protocol A–H. The original verifier adds 29 tests. Grouped decomposition: identity/reference/cycle tests exercise equal documents, shifted object IDs, and one self-cycle; object tests exercise direct dictionary add/remove/modify/type changes, array length, decoded stream bytes, and page content; page tests exercise one insertion, removal, reorder, inherited MediaBox/Resources/Rotate, and one insertion/edit alignment case; annotation tests exercise add/remove/Contents edit and order; structure/metadata tests exercise modified PageLayout, outline add/remove/retarget/ID independence, changed trailer ID, and modified Info; option tests exercise each option individually but only representative paths/kinds; API tests exercise Debug/re-exports, basic accessors, summary page counters, and render line count.

Reference probing established: empty→one yields PageAdded; an eight-level nested edit yields PageModified plus the /L7 field change; a page-12 edit yields changed_page_numbers=[12], no page-1 changes, and two page-12 changes; a field edit has summary total=2 and len=2; without_structure removes outline and trailer-ID changes; inherited and inline CropBox compare empty; changing annotation F yields AnnotationChanged; adding/removing Info and trailer/ID yields Added/Removed changes; same-length array element edits are reported; duplicate-page removal is a single PageRemoved. Suite scanning showed the demonstrated behaviors below were not pinned.

For every gap below, a plausible broken variant passed all 29 original verifier tests and its focused probe failed. Representative empirical results: shallow depth cap returned []; partial structure gating leaked outline/ID changes; post-filtered annotations left PageModified; omitted annotation F returned []; presence-only Info/ID comparisons returned empty; omitted CropBox inheritance emitted Added(CropBox); page-only summary total returned 1 vs len 2; one-digit parsing returned [1] vs [12]; naive page prefix matching included page 12 under page 1; resetting a chained option leaked Info/Title. The reference passed all nine remedy probes. /var/artifacts/updated_test.patch is a full replacement verifier, applies cleanly to a pristine checkout, and the reference passes all 38 updated tests.

Show less
Audited by Lyra
573.6s · 26 steps · 53 messages

Bypassed
The check was bypassed — nothing changed, and the reviewer will see the audit findings and the note below.

Decisions are final for this run — re-run the audit to start fresh.

Requirements coverage

covered
gapped
Tier 1
7 covered · 11 gapped — by 11 gaps
Stated directly in the spec

Provide Document::diff and Document::diff_with with the specified signatures and DocumentDiff return type.
DocumentDiff exposes changes and all specified query/render/summary methods; Change exposes path and kind.
DiffOptions defaults to all scopes enabled, and each without_* method disables its named scope while preserving the option value as a copy.
1 gap
DiffSummary has public page add/remove/move/modify counters, and total equals the complete number of changes.
1 gap
Change, ChangeKind, DiffOptions, DiffSummary, and DocumentDiff are crate-root re-exports and implement Debug.
Comparison dereferences indirect objects so logical equality is independent of object IDs.
Comparison always terminates on cyclic object graphs.
Dictionary keys report Added, Removed, Modified, or TypeChanged according to presence/value/type.
1 gap
Array length differences are LengthChanged, and differing decoded stream bytes are StreamContentChanged.
Pages are content-matched: insertion/removal/movement produces page-level kinds rather than positional cascades, while an in-place edit produces PageModified plus field changes.
1 gap
Effective inherited page attributes are compared, so inherited and inline representations of the same value are equal.
1 gap
Annotations are order-insensitive and additions, removals, and edits are reported with annotation-specific kinds.
1 gap
Structural comparison includes catalog entries, outlines, and trailer document ID; outline destinations compare target pages rather than raw IDs.
2 gaps
Info metadata is included in default comparison.
1 gap
Disabling a scope removes every change attributable only to that scope, including derived markers.
2 gaps
Every change uses readable canonical paths for pages, page fields, catalog fields, Info fields, and trailer ID.
changes_for_page returns exactly one requested page's changes, structural_changes returns only non-page changes, and changed_page_numbers includes every changed page number.
2 gaps
Summary page counters reflect their corresponding kinds, total equals all changes, and render emits one line per change.
1 gap
Tier 2
0 covered · 5 gapped — by 7 gaps
Entailed by interpretation — never stated outright

Structural comparison must recurse through nested logical content rather than silently treating sufficiently deep values as equal.
1 gap
Adding or removing the Info dictionary or trailer document ID is itself a reportable difference, not a silent no-op.
2 gaps
Option builder operations compose independently: disabling a later scope must not re-enable an earlier disabled scope.
1 gap
Page-path parsing must recognize complete decimal page tokens and enforce a path boundary, so page 1 and page 12 remain independent alternatives.
2 gaps
CropBox, like the named examples, is an inherited page attribute whose effective value must be resolved.
1 gap
Demonstrated Gaps

Each gap is one plausible broken implementation that passes the entire original test suite while violating the linked requirements — proven by a probe the reference passes and the broken build fails.

Severity (Crash / Wrong result / Cosmetic) = what the uncaught flaw would do in the wild; plausibility (High / Medium / Low) = how likely someone would actually write it. Hover any pill for its exact meaning.

Wrong result
high plausibility
Demonstrated
Deep nested dictionary edits can be silently dropped

Wrong result
high plausibility
Demonstrated
without_structure can disable only catalog comparison and leak outlines/trailer ID

Wrong result
high plausibility
Demonstrated
Annotation post-filtering can leave a spurious PageModified marker

Wrong result
high plausibility
Demonstrated
Annotation comparison can inspect only the tested Contents field

Wrong result
high plausibility
Demonstrated
Info metadata addition/removal can be treated as a no-op

Wrong result
high plausibility
Demonstrated
Trailer document ID addition/removal can be treated as a no-op

Wrong result
high plausibility
Demonstrated
CropBox inheritance can be omitted

Wrong result
high plausibility
Demonstrated
DiffSummary::total can count only page-level categories

Wrong result
high plausibility
Demonstrated
changed_page_numbers can truncate multi-digit page numbers

Wrong result
high plausibility
Demonstrated
changes_for_page can confuse page 1 with page 12

Wrong result
high plausibility
Demonstrated
Chained DiffOptions builders can re-enable an earlier disabled scope

Applies cleanly
Base tests pass
New tests fail on clean repo
Reference passes suite
Proposed tests (39)

Open patch & diff viewer
9 new · 1 modified · 29 carried over

outline_retarget_to_different_page_is_change
modified
rust
#[test]
fn outline_retarget_to_different_page_is_change() {
    let a = with_outline_to_page(0);
    let mut b = with_outline_to_page(0);
    let first_page = b.get_pages().values().copied().next().unwrap();
    let root = b.trailer.get(b"Root").unwrap().as_reference().unwrap();
    let ol = b.get_object(root).unwrap().as_dict().unwrap().get(b"Outlines").unwrap().as_reference().unwrap();
    let item = b.get_object(ol).unwrap().as_dict().unwrap().get(b"First").unwrap().as_reference().unwrap();
    b.get_object_mut(item).unwrap().as_dict_mut().unwrap().set("Dest", vec![first_page.into(), Object::Name(b"Fit".to_vec())]);
    assert!(a.diff(&b).iter().any(|c| kind_is(c, "OutlineChanged")), "retarget to a different page must be OutlineChanged: {:?}", a.diff(&b).changes);
}
 
fn set_page_value_for_completeness(doc: &mut Document, page_number: u32, key: &str, value: Object) {
    let page = *doc.get_pages().get(&page_number).unwrap();
Show 2 more lines
summary_total_includes_field_level_changes
new
rust
closes:
DiffSummary::total can count only page-level categories
#[test]
fn summary_total_includes_field_level_changes() {
    let mut a = simple(&[b"X"]);
    let mut b = simple(&[b"X"]);
    set_page_value_for_completeness(&mut a, 1, "K", 1i64.into());
    set_page_value_for_completeness(&mut b, 1, "K", 2i64.into());
    let d = a.diff(&b);
    assert!(d.len() > 1, "probe must contain both page and field changes: {:?}", d.changes);
    assert_eq!(d.summary().total(), d.len());
}
page_accessors_handle_multi_digit_page_boundaries
new
rust
closes:
changed_page_numbers can truncate multi-digit page numbers
changes_for_page can confuse page 1 with page 12
#[test]
fn page_accessors_handle_multi_digit_page_boundaries() {
    let bytes: Vec<Vec<u8>> = (1..=12).map(|i| format!("P{i}").into_bytes()).collect();
    let contents: Vec<&[u8]> = bytes.iter().map(Vec::as_slice).collect();
    let mut a = simple(&contents);
    let mut b = simple(&contents);
    set_page_value_for_completeness(&mut a, 12, "Rotate", 0i64.into());
    set_page_value_for_completeness(&mut b, 12, "Rotate", 90i64.into());
    let d = a.diff(&b);
    assert_eq!(d.changed_page_numbers(), vec![12]);
    assert!(d.changes_for_page(1).is_empty(), "page 1 must not include page 12: {:?}", d.changes_for_page(1));
    assert_eq!(d.changes_for_page(12).len(), 2, "{:?}", d.changes);
}
without_structure_suppresses_outlines_and_trailer
new
rust
closes:
without_structure can disable only catalog comparison and leak outlines/trailer ID
#[test]
fn without_structure_suppresses_outlines_and_trailer() {
    let mut a = with_outline_to_page(0);
    let mut b = simple(&[b"X", b"Y"]);
    a.trailer.set("ID", vec![Object::string_literal("A"), Object::string_literal("A")]);
    b.trailer.set("ID", vec![Object::string_literal("B"), Object::string_literal("B")]);
    assert!(!a.diff(&b).is_empty(), "probe must contain structural changes");
    let d = a.diff_with(&b, DiffOptions::default().without_structure());
    assert!(d.is_empty(), "all structural scopes must be disabled: {:?}", d.changes);
}
cropbox_inheritance_equals_inline
new
rust
closes:
CropBox inheritance can be omitted
#[test]
fn cropbox_inheritance_equals_inline() {
    let mut inherited = simple(&[b"X"]);
    let page = *inherited.get_pages().values().next().unwrap();
    let parent = inherited.get_object(page).unwrap().as_dict().unwrap()
        .get(b"Parent").unwrap().as_reference().unwrap();
    inherited.get_object_mut(parent).unwrap().as_dict_mut().unwrap()
        .set("CropBox", vec![0.into(), 0.into(), 500.into(), 700.into()]);
    let mut inline = simple(&[b"X"]);
    set_page_value_for_completeness(&mut inline, 1, "CropBox",
        Object::Array(vec![0.into(), 0.into(), 500.into(), 700.into()]));
    assert!(inherited.diff(&inline).is_empty(), "{:?}", inherited.diff(&inline).changes);
}
annotation_changes_include_flags
new
rust
closes:
Annotation comparison can inspect only the tested Contents field
#[test]
fn annotation_changes_include_flags() {
    let mk = |flags: i64| dictionary! {
        "Subtype"=>"Text", "Rect"=>vec![1.into(),2.into(),3.into(),4.into()], "F"=>flags
    };
    let d = with_annots(b"X", vec![mk(1)]).diff(&with_annots(b"X", vec![mk(2)]));
    assert!(d.iter().any(|c| kind_is(c, "AnnotationChanged")), "{:?}", d.changes);
}
info_and_trailer_id_presence_are_changes
new
rust
closes:
Info metadata addition/removal can be treated as a no-op
Trailer document ID addition/removal can be treated as a no-op
#[test]
fn info_and_trailer_id_presence_are_changes() {
    let plain = simple(&[b"X"]);
    let mut with_info = simple(&[b"X"]);
    let info = with_info.add_object(dictionary! { "Title"=>Object::string_literal("T") });
    with_info.trailer.set("Info", info);
    assert!(!plain.diff(&with_info).is_empty(), "adding Info must be reported");
    assert!(!with_info.diff(&plain).is_empty(), "removing Info must be reported");
 
    let mut with_id = simple(&[b"X"]);
    with_id.trailer.set("ID", vec![Object::string_literal("id"), Object::string_literal("id")]);
    assert!(!plain.diff(&with_id).is_empty(), "adding trailer/ID must be reported");
    assert!(!with_id.diff(&plain).is_empty(), "removing trailer/ID must be reported");
}
Show 8 more lines
deeply_nested_dictionary_changes_are_not_silently_dropped
new
rust
closes:
Deep nested dictionary edits can be silently dropped
#[test]
fn deeply_nested_dictionary_changes_are_not_silently_dropped() {
    let mut a = simple(&[b"X"]);
    let mut b = simple(&[b"X"]);
    set_page_value_for_completeness(&mut a, 1, "Deep", deeply_nested_value(1));
    set_page_value_for_completeness(&mut b, 1, "Deep", deeply_nested_value(2));
    let d = a.diff(&b);
    assert!(d.iter().any(|c| c.path.ends_with("/L7")), "{:?}", d.changes);
}
scope_builder_methods_compose
new
rust
closes:
Chained DiffOptions builders can re-enable an earlier disabled scope
#[test]
fn scope_builder_methods_compose() {
    let mut a = simple(&[b"X"]);
    let mut b = simple(&[b"X"]);
    let ia = a.add_object(dictionary! { "Title"=>Object::string_literal("A") });
    let ib = b.add_object(dictionary! { "Title"=>Object::string_literal("B") });
    a.trailer.set("Info", ia);
    b.trailer.set("Info", ib);
    set_catalog(&mut a, "PageLayout", Object::Name(b"One".to_vec()));
    set_catalog(&mut b, "PageLayout", Object::Name(b"Two".to_vec()));
    let options = DiffOptions::default().without_metadata().without_structure();
    assert!(a.diff_with(&b, options).is_empty(), "{:?}", a.diff_with(&b, options).changes);
}
without_annotations_removes_annotation_only_page_marker
new
rust
closes:
Annotation post-filtering can leave a spurious PageModified marker
#[test]
fn without_annotations_removes_annotation_only_page_marker() {
    let annot = dictionary! { "Subtype"=>"Text", "Rect"=>vec![1.into(),2.into(),3.into(),4.into()] };
    let none = with_annot(b"X", None);
    let one = with_annot(b"X", Some(annot));
    assert!(!none.diff(&one).is_empty(), "probe must contain an annotation change");
    let d = none.diff_with(&one, DiffOptions::default().without_annotations());
    assert!(d.is_empty(), "annotation-only changes must disappear entirely: {:?}", d.changes);
}
test.sh
unchanged
hunk
#!/usr/bin/env bash
set -uo pipefail
 
OUTPUT_PATH=""
MODE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --output_path)
      shift
      [ $# -gt 0 ] || { echo "missing value for --output_path" >&2; exit 2; }
      OUTPUT_PATH="$1"
      ;;
    --output_path=*)
      OUTPUT_PATH="${1#*=}"
Show 83 more lines
identical_documents_have_empty_diff
unchanged
rust
#[test]
fn identical_documents_have_empty_diff() {
    assert!(simple(&[b"A", b"B"]).diff(&simple(&[b"A", b"B"])).is_empty());
}
comparison_is_reference_independent
unchanged
rust
#[test]
fn comparison_is_reference_independent() {
    let a = build(0, &[b"same"], vec![]);
    let b = build(4, &[b"same"], vec![]);
    let pa: Vec<_> = a.get_pages().values().copied().collect();
    let pb: Vec<_> = b.get_pages().values().copied().collect();
    assert_ne!(pa, pb, "object ids must differ for a valid test");
    assert!(a.diff(&b).is_empty(), "{:?}", a.diff(&b).changes);
}
edited_content_reports_stream_and_page_modified
unchanged
rust
#[test]
fn edited_content_reports_stream_and_page_modified() {
    let d = simple(&[b"old"]).diff(&simple(&[b"new"]));
    assert!(d.iter().any(|c| c.path == "page 1/Contents" && kind_is(c, "StreamContentChanged")), "{:?}", d.changes);
    assert!(d.iter().any(|c| kind_is(c, "PageModified")), "{:?}", d.changes);
    assert!(!d.iter().any(|c| kind_is(c, "PageAdded") || kind_is(c, "PageRemoved")));
}
changed_dict_value_reports_modified
unchanged
rust
#[test]
fn changed_dict_value_reports_modified() {
    let a = build(0, &[b"x"], vec![("Rotate", 0i64.into())]);
    let b = build(0, &[b"x"], vec![("Rotate", 90i64.into())]);
    let d = a.diff(&b);
    assert!(d.iter().any(|c| c.path == "page 1/Rotate" && kind_is(c, "Modified")), "{:?}", d.changes);
}
added_and_removed_keys_reported
unchanged
rust
#[test]
fn added_and_removed_keys_reported() {
    let a = build(0, &[b"x"], vec![("Only", Object::string_literal("a"))]);
    let b = build(0, &[b"x"], vec![("Fresh", Object::string_literal("b"))]);
    let d = a.diff(&b);
    assert!(d.iter().any(|c| c.path == "page 1/Only" && kind_is(c, "Removed")), "{:?}", d.changes);
    assert!(d.iter().any(|c| c.path == "page 1/Fresh" && kind_is(c, "Added")), "{:?}", d.changes);
}
type_change_reported
unchanged
rust
#[test]
fn type_change_reported() {
    let a = build(0, &[b"x"], vec![("K", 1i64.into())]);
    let b = build(0, &[b"x"], vec![("K", Object::Name(b"n".to_vec()))]);
    assert!(a.diff(&b).iter().any(|c| c.path == "page 1/K" && kind_is(c, "TypeChanged")), "{:?}", a.diff(&b).changes);
}
array_length_change_reported
unchanged
rust
#[test]
fn array_length_change_reported() {
    let a = build(0, &[b"x"], vec![("Arr", Object::Array(vec![1.into(), 2.into()]))]);
    let b = build(0, &[b"x"], vec![("Arr", Object::Array(vec![1.into(), 2.into(), 3.into()]))]);
    assert!(a.diff(&b).iter().any(|c| c.path == "page 1/Arr" && kind_is(c, "LengthChanged")), "{:?}", a.diff(&b).changes);
}
inserted_page_is_single_add
unchanged
rust
#[test]
fn inserted_page_is_single_add() {
    let d = simple(&[b"P1", b"P2"]).diff(&simple(&[b"P1", b"NEW", b"P2"]));
    assert_eq!(d.len(), 1, "{:?}", d.changes);
    assert!(d.iter().any(|c| kind_is(c, "PageAdded")), "{:?}", d.changes);
}
removed_page_reported
unchanged
rust
#[test]
fn removed_page_reported() {
    let d = simple(&[b"P1", b"P2", b"P3"]).diff(&simple(&[b"P1", b"P3"]));
    assert_eq!(d.len(), 1, "{:?}", d.changes);
    assert!(d.iter().any(|c| kind_is(c, "PageRemoved")));
}
reordered_page_reported_as_move
unchanged
rust
#[test]
fn reordered_page_reported_as_move() {
    let d = simple(&[b"P1", b"P2", b"P3"]).diff(&simple(&[b"P1", b"P3", b"P2"]));
    assert!(d.iter().any(|c| kind_is(c, "PageMoved")), "{:?}", d.changes);
    assert!(!d.iter().any(|c| kind_is(c, "PageAdded") || kind_is(c, "PageRemoved")), "{:?}", d.changes);
}
inherited_attribute_equals_inline
unchanged
rust
#[test]
fn inherited_attribute_equals_inline() {
    let mut a = Document::with_version("1.5");
    let pages = a.new_object_id();
    let cid = a.add_object(Stream::new(dictionary!{}, b"X".to_vec()));
    let pid = a.add_object(dictionary!{ "Type"=>"Page","Parent"=>pages,"Contents"=>cid });
    a.objects.insert(pages, Object::Dictionary(dictionary!{ "Type"=>"Pages","Kids"=>vec![pid.into()],"Count"=>1,"MediaBox"=>mbox() }));
    let cat = a.add_object(dictionary!{ "Type"=>"Catalog","Pages"=>pages }); a.trailer.set("Root", cat);
    assert!(a.diff(&simple(&[b"X"])).is_empty(), "{:?}", a.diff(&simple(&[b"X"])).changes);
}
 
fn with_self_cycle(content: &[u8]) -> Document {
    let mut doc = simple(&[content]);
    let page = *doc.get_pages().values().next().unwrap();
Show 5 more lines
real_reference_cycle_terminates_and_diffs
unchanged
rust
#[test]
fn real_reference_cycle_terminates_and_diffs() {
    let a = with_self_cycle(b"old");
    let b = with_self_cycle(b"new");
    let node_a = a.get_object(*a.get_pages().values().next().unwrap()).unwrap()
        .as_dict().unwrap().get(b"Ring").unwrap().as_reference().unwrap();
    assert!(a.get_object(node_a).unwrap().as_dict().unwrap().get(b"Loop").unwrap().as_reference().unwrap() == node_a,
        "test must build a genuine self-referential object");
    let d = a.diff(&b);
    assert!(d.iter().any(|c| c.path == "page 1/Contents" && kind_is(c, "StreamContentChanged")), "{:?}", d.changes);
}
 
fn with_annot(page_content: &[u8], annot: Option<Dictionary>) -> Document {
    let mut doc = simple(&[page_content]);
Show 8 more lines
annotation_add_remove_change
unchanged
rust
#[test]
fn annotation_add_remove_change() {
    let a1 = dictionary!{ "Subtype"=>"Text","Rect"=>vec![1.into(),2.into(),3.into(),4.into()],"Contents"=>Object::string_literal("v1") };
    let a2 = dictionary!{ "Subtype"=>"Text","Rect"=>vec![1.into(),2.into(),3.into(),4.into()],"Contents"=>Object::string_literal("v2") };
    let none = with_annot(b"X", None);
    let one = with_annot(b"X", Some(a1.clone()));
    let changed = with_annot(b"X", Some(a2));
    assert!(none.diff(&one).iter().any(|c| kind_is(c, "AnnotationAdded")), "add");
    assert!(one.diff(&none).iter().any(|c| kind_is(c, "AnnotationRemoved")), "remove");
    let ch = one.diff(&changed);
    let reported_changed = ch.iter().any(|c| kind_is(c, "AnnotationChanged"));
    let reported_replace = ch.iter().any(|c| kind_is(c, "AnnotationRemoved"))
        && ch.iter().any(|c| kind_is(c, "AnnotationAdded"));
    assert!(reported_changed || reported_replace, "in-place annotation edit must be reported: {:?}", ch.changes);
Show 6 more lines
catalog_structure_change_reported
unchanged
rust
#[test]
fn catalog_structure_change_reported() {
    let mut a = simple(&[b"X"]); let mut b = simple(&[b"X"]);
    set_catalog(&mut a, "PageLayout", Object::Name(b"SinglePage".to_vec()));
    set_catalog(&mut b, "PageLayout", Object::Name(b"TwoColumnLeft".to_vec()));
    assert!(a.diff(&b).contains_path("catalog/PageLayout"), "{:?}", a.diff(&b).changes);
}
 
fn with_outline(title: &str, dest_page: i64) -> Document {
    let mut doc = simple(&[b"X"]);
    let page = *doc.get_pages().values().next().unwrap();
    let ol = doc.add_object(dictionary!{ "Type"=>"Outlines","Count"=>1 });
    let item = doc.add_object(dictionary!{ "Title"=>Object::string_literal(title),"Parent"=>ol,
        "Dest"=>vec![page.into(), Object::Name(b"XYZ".to_vec()), dest_page.into()] });
Show 5 more lines
outline_add_and_remove
unchanged
rust
#[test]
fn outline_add_and_remove() {
    let plain = simple(&[b"X"]);
    let ch1 = with_outline("Intro", 0);
    assert!(plain.diff(&ch1).iter().any(|c| kind_is(c, "OutlineAdded")), "add: {:?}", plain.diff(&ch1).changes);
    assert!(ch1.diff(&plain).iter().any(|c| kind_is(c, "OutlineRemoved")), "remove: {:?}", ch1.diff(&plain).changes);
}
trailer_id_change_reported
unchanged
rust
#[test]
fn trailer_id_change_reported() {
    let mut a = simple(&[b"X"]); let mut b = simple(&[b"X"]);
    a.trailer.set("ID", vec![Object::string_literal("id-a"), Object::string_literal("id-a")]);
    b.trailer.set("ID", vec![Object::string_literal("id-b"), Object::string_literal("id-b")]);
    assert!(a.diff(&b).iter().any(|c| c.path.starts_with("trailer/ID")), "{:?}", a.diff(&b).changes);
}
info_metadata_change_reported
unchanged
rust
#[test]
fn info_metadata_change_reported() {
    let mut a = simple(&[b"X"]); let mut b = simple(&[b"X"]);
    let ia = a.add_object(dictionary!{ "Title"=>Object::string_literal("Old") }); a.trailer.set("Info", ia);
    let ib = b.add_object(dictionary!{ "Title"=>Object::string_literal("New") }); b.trailer.set("Info", ib);
    assert!(a.diff(&b).contains_path("Info/Title"), "{:?}", a.diff(&b).changes);
}
options_toggle_scopes
unchanged
rust
#[test]
fn options_toggle_scopes() {
    let mut a = simple(&[b"X"]); let mut b = simple(&[b"X"]);
    let ia = a.add_object(dictionary!{ "Title"=>Object::string_literal("A") }); a.trailer.set("Info", ia);
    let ib = b.add_object(dictionary!{ "Title"=>Object::string_literal("B") }); b.trailer.set("Info", ib);
    set_catalog(&mut a, "PageLayout", Object::Name(b"One".to_vec()));
    set_catalog(&mut b, "PageLayout", Object::Name(b"Two".to_vec()));
    assert!(a.diff_with(&b, DiffOptions::default().without_metadata()).iter().all(|c| c.path != "Info/Title"));
    assert!(a.diff_with(&b, DiffOptions::default().without_structure()).iter().all(|c| !c.path.starts_with("catalog")));
}
option_without_annotations_drops_annotation_changes
unchanged
rust
#[test]
fn option_without_annotations_drops_annotation_changes() {
    let annot = dictionary!{ "Subtype"=>"Text","Rect"=>vec![1.into(),2.into(),3.into(),4.into()] };
    let none = with_annot(b"X", None);
    let one = with_annot(b"X", Some(annot));
    assert!(none.diff(&one).iter().any(|c| kind_is(c, "AnnotationAdded")));
    let d = none.diff_with(&one, DiffOptions::default().without_annotations());
    assert!(d.iter().all(|c| !(kind_is(c, "AnnotationAdded") || kind_is(c, "AnnotationRemoved") || kind_is(c, "AnnotationChanged"))), "{:?}", d.changes);
}
summary_and_render_reflect_changes
unchanged
rust
#[test]
fn summary_and_render_reflect_changes() {
    let d = simple(&[b"P1", b"P2"]).diff(&simple(&[b"P1", b"NEW", b"P2"]));
    let s: DiffSummary = d.summary();
    assert_eq!(s.pages_added, 1);
    assert_eq!(s.total(), d.len());
    assert!(d.changed_page_numbers().contains(&2));
 
    let moved = simple(&[b"P1", b"P2", b"P3"]).diff(&simple(&[b"P1", b"P3", b"P2"]));
    assert!(moved.summary().pages_moved >= 1, "{:?}", moved.changes);
    let removed = simple(&[b"P1", b"P2"]).diff(&simple(&[b"P1"]));
    assert_eq!(removed.summary().pages_removed, 1, "{:?}", removed.changes);
    let edited = simple(&[b"a"]).diff(&simple(&[b"b"]));
    assert_eq!(edited.summary().pages_modified, 1, "{:?}", edited.changes);
Show 1 more lines
stream_comparison_ignores_compression
unchanged
rust
#[test]
fn stream_comparison_ignores_compression() {
    let content = "BT (line of repeated content here) Tj ET\n".repeat(200).into_bytes();
    let mut a = Document::with_version("1.5");
    let pages = a.new_object_id();
    let mut stream = Stream::new(dictionary!{}, content.clone());
    stream.compress().unwrap();
    assert_ne!(stream.content, content, "test needs genuinely compressed bytes");
    let cid = a.add_object(stream);
    let pid = a.add_object(dictionary!{ "Type"=>"Page","Parent"=>pages,"Contents"=>cid,"MediaBox"=>mbox() });
    a.objects.insert(pages, Object::Dictionary(dictionary!{ "Type"=>"Pages","Kids"=>vec![pid.into()],"Count"=>1 }));
    let cat = a.add_object(dictionary!{ "Type"=>"Catalog","Pages"=>pages }); a.trailer.set("Root", cat);
    let b = simple(&[&content]);
    assert!(a.diff(&b).is_empty(), "compression must not count as a change: {:?}", a.diff(&b).changes);
Show 1 more lines
page_and_structural_accessors
unchanged
rust
#[test]
fn page_and_structural_accessors() {
    let mut a = simple(&[b"P1", b"P2"]);
    let mut b = simple(&[b"P1", b"EDIT"]);
    set_catalog(&mut a, "PageLayout", Object::Name(b"One".to_vec()));
    set_catalog(&mut b, "PageLayout", Object::Name(b"Two".to_vec()));
    let d = a.diff(&b);
    assert!(d.changes_for_page(2).iter().all(|c| c.path.starts_with("page 2")));
    assert!(!d.changes_for_page(2).is_empty());
    assert!(d.structural_changes().iter().all(|c| !c.path.starts_with("page ")));
    assert!(d.structural_changes().iter().any(|c| c.path == "catalog/PageLayout"));
}
 
fn with_annots(content: &[u8], annots: Vec<Dictionary>) -> Document {
Show 6 more lines
annotation_comparison_ignores_order
unchanged
rust
#[test]
fn annotation_comparison_ignores_order() {
    let mk = |x: i64| dictionary!{ "Subtype"=>"Text","Rect"=>vec![x.into(),0.into(),0.into(),0.into()] };
    let a = with_annots(b"X", vec![mk(1), mk(2)]);
    let b = with_annots(b"X", vec![mk(2), mk(1)]);
    let d = a.diff(&b);
    assert!(d.iter().all(|c| !(kind_is(c, "AnnotationAdded") || kind_is(c, "AnnotationRemoved") || kind_is(c, "AnnotationChanged"))), "reorder must be no-op: {:?}", d.changes);
}
inheritance_covers_resources_and_rotate
unchanged
rust
#[test]
fn inheritance_covers_resources_and_rotate() {
    fn on_parent(res_key: &str) -> Document {
        let mut doc = Document::with_version("1.5");
        let pages = doc.new_object_id();
        let cid = doc.add_object(Stream::new(dictionary!{}, b"X".to_vec()));
        let pid = doc.add_object(dictionary!{ "Type"=>"Page","Parent"=>pages,"Contents"=>cid });
        doc.objects.insert(pages, Object::Dictionary(dictionary!{ "Type"=>"Pages","Kids"=>vec![pid.into()],"Count"=>1,
            "MediaBox"=>mbox(), "Resources"=>dictionary!{ "K"=>Object::Name(res_key.as_bytes().to_vec()) }, "Rotate"=>90i64 }));
        let cat = doc.add_object(dictionary!{ "Type"=>"Catalog","Pages"=>pages }); doc.trailer.set("Root", cat);
        doc
    }
    fn inline(res_key: &str) -> Document {
        build(0, &[b"X"], vec![
Show 6 more lines
render_prints_one_line_per_change
unchanged
rust
#[test]
fn render_prints_one_line_per_change() {
    let d = simple(&[b"P1", b"P2"]).diff(&simple(&[b"P1", b"NEW", b"P2", b"MORE"]));
    assert!(!d.is_empty());
    assert_eq!(d.render().lines().count(), d.len());
}
public_types_are_reexported_and_debug
unchanged
rust
#[test]
fn public_types_are_reexported_and_debug() {
    use lopdf::{Change, ChangeKind, DiffOptions, DiffSummary, DocumentDiff};
    let d: DocumentDiff = simple(&[b"a"]).diff(&simple(&[b"b"]));
    let _ = format!("{d:?}");
    let _ = format!("{:?}", DiffOptions::default());
    let summary: DiffSummary = d.summary();
    let _ = format!("{summary:?}");
    let change: &Change = d.iter().next().expect("expected a change");
    let kind: &ChangeKind = &change.kind;
    let _ = format!("{kind:?}");
}
insertion_before_edited_page_keeps_alignment
unchanged
rust
#[test]
fn insertion_before_edited_page_keeps_alignment() {
    let a = build(0, &[b"AAA", b"BBB"], vec![]);
    let b = build(0, &[b"INSERTED", b"AAA", b"BBB"], vec![("Rotate", 90i64.into())]);
    let d = a.diff(&b);
    assert!(d.iter().any(|c| kind_is(c, "PageAdded")), "inserted page not reported: {:?}", d.changes);
    assert!(!d.iter().any(|c| kind_is(c, "StreamContentChanged")), "spurious content change from mispairing: {:?}", d.changes);
    assert!(d.iter().any(|c| c.path.ends_with("/Rotate")), "the real edit was lost: {:?}", d.changes);
}
 
fn with_outline_to_page(shift: usize) -> Document {
    let mut doc = build(shift, &[b"X", b"Y"], vec![]);
    let target = doc.get_pages().values().copied().nth(1).unwrap();
    let ol = doc.add_object(dictionary!{ "Type"=>"Outlines","Count"=>1 });
Show 7 more lines
outline_identical_under_different_ids_is_no_change
unchanged
rust
#[test]
fn outline_identical_under_different_ids_is_no_change() {
    let a = with_outline_to_page(0);
    let b = with_outline_to_page(6);
    let ta: Vec<_> = a.get_pages().values().copied().collect();
    let tb: Vec<_> = b.get_pages().values().copied().collect();
    assert_ne!(ta, tb, "object ids must differ for a valid test");
    let d = a.diff(&b);
    assert!(d.iter().all(|c| !(kind_is(c, "OutlineChanged") || kind_is(c, "OutlineAdded") || kind_is(c, "OutlineRemoved"))),
        "spurious outline change from comparing raw ids: {:?}", d.changes);
    assert!(d.is_empty(), "identical documents must produce no changes: {:?}", d.changes);
}
Hide carried-over tests

Report an issue

Help









2:

Shipd
/
olympus
Home
Events
Submissions
Payouts

587/600
2
Silver
Create
· $150–350
61
Verifier Completeness Audit
Import repositories from fast-import streams

Back to submission
Task description


Add FastImport to the repository, taking the stream reader and *FastImportOptions, returning a *FastImportResult with the objects and references git makes.

Comment lines, blank lines and progress are ignored wherever a command or its fields are read; done ends the stream. A blob command stores a blob; data arrives counted with a byte length, or delimited as in data <<EOT, and may be any bytes. A mark line like mark :7 remembers the object just created, later :7; a mark never set fails, as does any malformed line, each a *FastImportError whose Line is the offending 1-based line.

A commit names a reference and carries an optional author, a required committer with timestamp and timezone, an optional encoding, a message, an optional from, merge lines, then file actions. filemodify adds or replaces a path with mode 100644, 100755, 120000 or 160000 (a gitlink names a commit hash that need not exist locally) with content from a mark, a full hash, or inline data; filedelete removes a path or subtree; filecopy and filerename move a file or directory, a rename never losing content, even to the same path or its own subtree; deleteall clears it. A path action replaces whatever stood there, file and directory displacing each other. Paths must be canonical and may be quoted with usual escapes.

The tree a branch reached after one commit is where its next starts; streams interleave freely, from restarts a branch at a revision, merge adds parents in order. A branch not seen earlier starts fresh even when the reference exists; only from attaches history. Revisions in from, merge and tag accept marks, full hashes and reference names.

A tag creates an annotated tag with tagger and message; reset points a reference at a revision, or with no from starts an orphan branch for the next commit, dropping any same-stream commit staged for it and leaving a stored reference alone.

References move only at stream completion or a checkpoint: a failing stream leaves every reference where it was, though written objects may exist; a checkpoint makes all durable, all-or-nothing. When a stored reference and the tip are both commits and the tip is not a descendant, the update is skipped and the name added to the result's SkippedRefs, a string slice; Force overrides this; a non-commit reference always updates. Its integer Blobs, Commits and Tags fields count distinct objects newly stored, not repeats or ones already present.

Marks survive runs: the ExportMarks writer receives every mark with its final hash when the stream ends, one per line as git writes them; the ImportMarks reader seeds the table first, so an incremental stream builds on them.

Identity lines are reproduced exactly, negative seconds and a -0000 distinct from +0000 included; an offset outside -1400..+1400 fails. The importer works the same on filesystem and in-memory storages, never touches the worktree, and objects are byte-identical to git, so a fast-export stream of these commands reproduces its repository, verified by hash.
Incomplete
5 demonstrated
The audit demonstrated 5 gaps where a broken implementation could still pass the current tests. Review the proposed test patch below.

Audited the 107-test verifier against the task text, implementation oracle, and adversarial mutations. The original tests broadly cover API shape; counted/delimited/binary data; marks; commit metadata; branch carry, from, merges, and interleaving; all file actions and path conflicts; tags/resets; checkpoints and reference rollback; fast-forward/Force behavior; storage/worktree/hash fidelity; and many malformed-line cases. Oracle probes additionally covered both timezone bounds, repeated pre-existing tags, a blob-mark tag target, inline symlink data, malformed imported marks, and ExportMarks writer failure. Five oracle-backed behaviors were not pinned. For each, an individually plausible mutation passed all 107 original FastImport tests (go test . -run '^TestFastImportB47e2d') and failed its oracle probe. The replacement patch adds five tests (112 total); it applies cleanly to a pristine worktree, passes the reference (./test.sh --output_path ... new: 112 tests, 0 failures), and its five added tests reject the combined broken mutations. /var/artifacts/updated_test.patch was written as a full replacement (SHA-256 1c2158ea78e7eeb9dac6fc5b74938fa53a2cce907fed451fa2eda345071d8a91).

Show less
Audited by Lyra
933.1s · 54 steps · 109 messages

Decision
4/4 validation checks passed

Accept as-is
Apply the proposed patch
Accept with edits
Edit on patch page

Bypass check
Keep your tests — the reviewer will be notified
Note for the reviewer (optional)
Context for whoever reviews this submission…
Submit decision
Requirements coverage

covered
gapped
Tier 1
11 covered · 6 gapped — by 5 gaps
Stated directly in the spec

Repository.FastImport must accept a stream reader and *FastImportOptions and return a *FastImportResult describing created objects and references.
Comments, blank lines, and progress records are ignored at command and field-reading positions, while done terminates parsing and prevents fall-through into later input.
Blob data supports exact counted lengths and delimiter form and can contain arbitrary bytes, including empty, binary, and non-newline-terminated content.
Marks remember the object just created; undeclared marks and malformed stream lines return *FastImportError with the offending one-based line.
Commits support optional author, required exact committer identity/timezone, optional encoding, message, optional from, ordered merges, and then file actions.
filemodify supports modes 100644, 100755, 120000, and 160000 and the applicable mark, full-hash, and inline content forms; gitlinks may name an absent commit hash.
1 gap
Delete removes a file or subtree; copy and rename handle files/directories; rename preserves content for self/descendant destinations; deleteall clears; and path actions enforce file/directory displacement.
Paths must be canonical, and quoted paths must implement the usual escapes while rejecting malformed or noncanonical results.
Branch state carries between same-stream commits, branches can interleave, from replaces inherited state/history, merges preserve parent order, and an unseen branch does not implicitly attach to an existing stored reference.
from, merge, and tag revision operands accept marks, full hashes, and reference names, with context-appropriate object-type handling rather than one generic commit-only rule.
1 gap
tag creates an annotated tag; reset with from points a ref, while bare reset establishes orphan state, cancels same-stream staging for that ref, and leaves a stored ref unchanged.
1 gap
References are delayed until completion/checkpoint, failures preserve refs since the last checkpoint, and each checkpoint update is atomic.
Non-fast-forward commit ref updates are skipped and reported unless Force is set; non-commit refs update normally.
Blobs, Commits, and Tags each count only distinct newly stored objects, excluding duplicates in a run and objects already present from earlier runs.
1 gap
Marks persist across runs: ImportMarks seeds the table before parsing and ExportMarks receives every final mark/hash pair at successful completion.
1 gap
Identity bytes must be reproduced exactly, including negative timestamps and signed zero timezone, and offsets on either side outside the inclusive -1400..+1400 range must fail.
1 gap
The importer behaves equivalently on filesystem and memory storage, does not alter the worktree, and emits Git-byte-identical objects suitable for fast-export round trips.
Tier 2
0 covered · 2 gapped — by 2 gaps
Entailed by interpretation — never stated outright

The listed filemodify data-source alternatives are independent for non-gitlink blob-backed modes: in particular, symlink mode 120000 accepts inline data rather than inheriting gitlink's commit-only restriction.
1 gap
FastImport must not silently report success when ExportMarks cannot receive the promised final mark table; writer errors must be returned.
1 gap
Demonstrated Gaps

Each gap is one plausible broken implementation that passes the entire original test suite while violating the linked requirements — proven by a probe the reference passes and the broken build fails.

Severity (Crash / Wrong result / Cosmetic) = what the uncaught flaw would do in the wild; plausibility (High / Medium / Low) = how likely someone would actually write it. Hover any pill for its exact meaning.

Wrong result
high plausibility
Demonstrated
Inline symlink data can be incorrectly rejected

Wrong result
high plausibility
Demonstrated
Repeated annotated tag objects may be over-counted

Wrong result
high plausibility
Demonstrated
Negative timezone offsets below -1400 can be accepted

Wrong result
medium plausibility
Demonstrated
Tag resolution can be wrongly restricted to commits

Wrong result
medium plausibility
Demonstrated
ExportMarks writer errors can be silently ignored

Applies cleanly
Base tests pass
New tests fail on clean repo
Reference passes suite
Proposed tests (115)

Open patch & diff viewer
5 new · 1 modified · 109 carried over

TestFastImportB47e2dConflictingRefsRollBackAtomically
modified
go
func TestFastImportB47e2dConflictingRefsRollBackAtomically(t *testing.T) {
	t.Parallel()
	probe := b47e2dRepo(t)
	b47e2dImport(t, probe, "blob\nmark :1\ndata 2\nx\n"+
		"commit refs/heads/a\ncommitter t <t@t> 1 +0000\ndata 3\nc1\nM 100644 :1 f\n", nil)
	firstCommit := b47e2dRef(t, probe, "refs/heads/a")
 
	fs := memfs.New()
	dot, err := fs.Chroot(".git")
	require.NoError(t, err)
	r, err := Init(filesystem.NewStorage(dot, cache.NewObjectLRUDefault()))
	require.NoError(t, err)
 
	stream := "blob\nmark :1\ndata 2\nx\n" +
Show 15 more lines
TestFastImportB47e2dSymlinkInlineData
new
go
closes:
Inline symlink data can be incorrectly rejected
func TestFastImportB47e2dSymlinkInlineData(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	stream := "commit refs/heads/m\ncommitter t <t@t> 1 +0000\ndata 1\nm\n" +
		"M 120000 inline link\ndata 6\ntarget\n"
	b47e2dImport(t, r, stream, nil)
 
	c := b47e2dCommit(t, r, b47e2dRef(t, r, "refs/heads/m"))
	tree, err := c.Tree()
	require.NoError(t, err)
	entry, err := tree.FindEntry("link")
	require.NoError(t, err)
	require.Equal(t, filemode.Symlink, entry.Mode)
	require.Equal(t, "target", b47e2dFile(t, c, "link"))
Show 1 more lines
TestFastImportB47e2dTagMayTargetBlobMark
new
go
closes:
Tag resolution can be wrongly restricted to commits
func TestFastImportB47e2dTagMayTargetBlobMark(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	stream := "blob\nmark :1\ndata 1\nx\n" +
		"tag blobtag\nfrom :1\ntagger t <t@t> 1 +0000\ndata 1\nm\n"
	b47e2dImport(t, r, stream, nil)
 
	tag, err := r.TagObject(b47e2dRef(t, r, "refs/tags/blobtag"))
	require.NoError(t, err)
	require.Equal(t, plumbing.BlobObject, tag.TargetType)
	require.Equal(t, plumbing.NewHash("c1b0730e0133447badcfd47fd144e254807b06e1"), tag.Target)
}
TestFastImportB47e2dRepeatedTagNotCountedAgain
new
go
closes:
Repeated annotated tag objects may be over-counted
func TestFastImportB47e2dRepeatedTagNotCountedAgain(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	stream := "blob\nmark :1\ndata 1\nx\n" +
		"tag blobtag\nfrom :1\ntagger t <t@t> 1 +0000\ndata 1\nm\n"
	first := b47e2dImport(t, r, stream, nil)
	second := b47e2dImport(t, r, stream, nil)
 
	require.Equal(t, 1, first.Tags)
	require.Equal(t, 0, second.Tags)
}
TestFastImportB47e2dTimezoneLowerBoundary
new
go
closes:
Negative timezone offsets below -1400 can be accepted
func TestFastImportB47e2dTimezoneLowerBoundary(t *testing.T) {
	t.Parallel()
	good := b47e2dRepo(t)
	b47e2dImport(t, good,
		"commit refs/heads/m\ncommitter t <t@t> 1 -1400\ndata 1\nm\n", nil)
 
	bad := b47e2dRepo(t)
	_, err := bad.FastImport(strings.NewReader(
		"commit refs/heads/m\ncommitter t <t@t> 1 -1401\ndata 1\nm\n"), nil)
	require.Error(t, err)
	require.Equal(t, 2, b47e2dErrLine(t, err))
}
TestFastImportB47e2dExportMarksWriterErrorPropagated
new
go
closes:
ExportMarks writer errors can be silently ignored
func TestFastImportB47e2dExportMarksWriterErrorPropagated(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	_, err := r.FastImport(strings.NewReader("blob\nmark :1\ndata 1\nx\n"),
		&FastImportOptions{ExportMarks: b47e2dClosedWriter{}})
	require.ErrorIs(t, err, os.ErrClosed)
}
TestFastImportB47e2dSingleCommitGolden
unchanged
go
func TestFastImportB47e2dSingleCommitGolden(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	res := b47e2dImport(t, r, b47e2dStreamG1, nil)
 
	require.Equal(t, 1, res.Blobs)
	require.Equal(t, 1, res.Commits)
	require.Equal(t, 0, res.Tags)
	require.Equal(t, "9e0e0679776bffc4ed1e980c6f6c308c700f2ac6", b47e2dRef(t, r, "refs/heads/master").String())
}
TestFastImportB47e2dBlobContentAndModes
unchanged
go
func TestFastImportB47e2dBlobContentAndModes(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	b47e2dImport(t, r, b47e2dStreamG1, nil)
 
	c := b47e2dCommit(t, r, b47e2dRef(t, r, "refs/heads/master"))
	require.Equal(t, "alpha\n", b47e2dFile(t, c, "a.txt"))
	require.Equal(t, "alpha\n", b47e2dFile(t, c, "tools/run.sh"))
 
	tree, err := c.Tree()
	require.NoError(t, err)
	e, err := tree.FindEntry("tools/run.sh")
	require.NoError(t, err)
	require.Equal(t, filemode.Executable, e.Mode)
Show 1 more lines
TestFastImportB47e2dIdentityFidelity
unchanged
go
func TestFastImportB47e2dIdentityFidelity(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	b47e2dImport(t, r, b47e2dStreamG1, nil)
 
	c := b47e2dCommit(t, r, b47e2dRef(t, r, "refs/heads/master"))
	require.Equal(t, "An Author", c.Author.Name)
	require.Equal(t, "author@example.com", c.Author.Email)
	require.Equal(t, int64(1709287200), c.Author.When.Unix())
	require.Equal(t, "A Committer", c.Committer.Name)
	require.Equal(t, int64(1709290800), c.Committer.When.Unix())
	_, offset := c.Committer.When.Zone()
	require.Equal(t, 90*60, offset)
	require.Equal(t, "first subject\n", c.Message)
Show 1 more lines
TestFastImportB47e2dInterleavedBranches
unchanged
go
func TestFastImportB47e2dInterleavedBranches(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	res := b47e2dImport(t, r, b47e2dStreamG4, nil)
 
	require.Equal(t, 4, res.Commits)
	require.Equal(t, "f3a17cb28d6d74a4ac66bfeead1024ede0cdde1a", b47e2dRef(t, r, "refs/heads/b1").String())
	require.Equal(t, "718a543df95a99bf02921b854dbcd1ab7831a206", b47e2dRef(t, r, "refs/heads/b2").String())
	require.Equal(t, "94461debd5bb7244b6f3d8677fb6f520c353dc26", b47e2dRef(t, r, "refs/heads/b3").String())
}
TestFastImportB47e2dOctopusMergeParents
unchanged
go
func TestFastImportB47e2dOctopusMergeParents(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	b47e2dImport(t, r, b47e2dStreamG4, nil)
 
	h := b47e2dRef(t, r, "refs/heads/master")
	require.Equal(t, "06319ec4ad77f84048164f0921809c5d74236dc9", h.String())
 
	c := b47e2dCommit(t, r, h)
	require.Len(t, c.ParentHashes, 3)
	require.Equal(t, "f3a17cb28d6d74a4ac66bfeead1024ede0cdde1a", c.ParentHashes[0].String())
	require.Equal(t, "718a543df95a99bf02921b854dbcd1ab7831a206", c.ParentHashes[1].String())
	require.Equal(t, "94461debd5bb7244b6f3d8677fb6f520c353dc26", c.ParentHashes[2].String())
}
TestFastImportB47e2dFromLoadsThatTree
unchanged
go
func TestFastImportB47e2dFromLoadsThatTree(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	b47e2dImport(t, r, b47e2dStreamG4, nil)
 
	c := b47e2dCommit(t, r, b47e2dRef(t, r, "refs/heads/master"))
	require.Equal(t, "a\n", b47e2dFile(t, c, "f0"))
	require.Equal(t, "a\n", b47e2dFile(t, c, "f1"))
	_, err := c.File("f2")
	require.Error(t, err)
	_, err = c.File("f3")
	require.Error(t, err)
}
TestFastImportB47e2dDirectoryCopyAndRename
unchanged
go
func TestFastImportB47e2dDirectoryCopyAndRename(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	b47e2dImport(t, r, b47e2dStreamG5, nil)
 
	tip := b47e2dCommit(t, r, b47e2dRef(t, r, "refs/heads/master"))
	require.Len(t, tip.ParentHashes, 1)
	mid := b47e2dCommit(t, r, tip.ParentHashes[0])
 
	require.Equal(t, "a\n", b47e2dFile(t, mid, "copydir/one"))
	require.Equal(t, "b\n", b47e2dFile(t, mid, "copydir/two"))
	require.Equal(t, "b\n", b47e2dFile(t, mid, "dir/two"))
	require.Equal(t, "a\n", b47e2dFile(t, mid, "moved"))
	require.Equal(t, "a\n", b47e2dFile(t, mid, "top"))
Show 3 more lines
TestFastImportB47e2dDeleteAll
unchanged
go
func TestFastImportB47e2dDeleteAll(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	b47e2dImport(t, r, b47e2dStreamG5, nil)
 
	require.Equal(t, "b1bc640bd5ebe5ed96056ac11fa5abdcfa7a56bf", b47e2dRef(t, r, "refs/heads/master").String())
 
	tip := b47e2dCommit(t, r, b47e2dRef(t, r, "refs/heads/master"))
	require.Equal(t, "b\n", b47e2dFile(t, tip, "only.txt"))
	_, err := tip.File("top")
	require.Error(t, err)
}
TestFastImportB47e2dSequentialBranchCarry
unchanged
go
func TestFastImportB47e2dSequentialBranchCarry(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	b47e2dImport(t, r, b47e2dStreamG5, nil)
 
	depth := 0
	c := b47e2dCommit(t, r, b47e2dRef(t, r, "refs/heads/master"))
	for {
		depth++
		if c.NumParents() == 0 {
			break
		}
		var err error
		c, err = c.Parent(0)
Show 4 more lines
TestFastImportB47e2dDelimitedDataAndQuotedPaths
unchanged
go
func TestFastImportB47e2dDelimitedDataAndQuotedPaths(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	b47e2dImport(t, r, b47e2dStreamG6, nil)
 
	require.Equal(t, "4d3fb5b27ef3564e920c830c5cbe10aa156ee7ea", b47e2dRef(t, r, "refs/heads/master").String())
 
	c := b47e2dCommit(t, r, b47e2dRef(t, r, "refs/heads/master"))
	require.Equal(t, "line one\nline two\n", b47e2dFile(t, c, "plain.txt"))
	require.Equal(t, "line one\nline two\n", b47e2dFile(t, c, `sp ace/quo"te\back.txt`))
}
TestFastImportB47e2dFileDirReplacement
unchanged
go
func TestFastImportB47e2dFileDirReplacement(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	b47e2dImport(t, r, b47e2dStreamG9, nil)
 
	require.Equal(t, "e83f21258afb8164fbf94af06752eb1a07b4dfb2", b47e2dRef(t, r, "refs/heads/master").String())
 
	c := b47e2dCommit(t, r, b47e2dRef(t, r, "refs/heads/master"))
	require.Equal(t, "x\n", b47e2dFile(t, c, "p/child"))
	require.Equal(t, "x\n", b47e2dFile(t, c, "q"))
	_, err := c.File("p")
	require.Error(t, err)
	_, err = c.File("q/inner")
	require.Error(t, err)
Show 1 more lines
TestFastImportB47e2dTreeOrderGitlinkSymlink
unchanged
go
func TestFastImportB47e2dTreeOrderGitlinkSymlink(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	b47e2dImport(t, r, b47e2dStreamG10, nil)
 
	require.Equal(t, "c2ca0a3ace0428052c51458a97d767200548dde5", b47e2dRef(t, r, "refs/heads/master").String())
 
	c := b47e2dCommit(t, r, b47e2dRef(t, r, "refs/heads/master"))
	tree, err := c.Tree()
	require.NoError(t, err)
 
	sub, err := tree.FindEntry("sub")
	require.NoError(t, err)
	require.Equal(t, filemode.Submodule, sub.Mode)
Show 6 more lines
TestFastImportB47e2dAnnotatedTag
unchanged
go
func TestFastImportB47e2dAnnotatedTag(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	res := b47e2dImport(t, r, b47e2dStreamG8, nil)
 
	require.Equal(t, 1, res.Tags)
	require.Equal(t, "ed94c0539535ff8c8dde526baf810e0695cbca7a", b47e2dRef(t, r, "refs/tags/release-1").String())
 
	tag, err := r.TagObject(b47e2dRef(t, r, "refs/tags/release-1"))
	require.NoError(t, err)
	require.Equal(t, "release-1", tag.Name)
	require.Equal(t, "Tagger T", tag.Tagger.Name)
	require.Equal(t, "tag@example.com", tag.Tagger.Email)
	require.Equal(t, "tag message\n", tag.Message)
Show 3 more lines
TestFastImportB47e2dResetCreatesRefs
unchanged
go
func TestFastImportB47e2dResetCreatesRefs(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	b47e2dImport(t, r, b47e2dStreamG11, nil)
 
	want := "0ccaa824fa6c8f894b90fd2363d2c315cf342cfe"
	require.Equal(t, want, b47e2dRef(t, r, "refs/heads/master").String())
	require.Equal(t, want, b47e2dRef(t, r, "refs/heads/copy").String())
	require.Equal(t, want, b47e2dRef(t, r, "refs/tags/light").String())
}
TestFastImportB47e2dResetOrphanRestart
unchanged
go
func TestFastImportB47e2dResetOrphanRestart(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	stream := b47e2dStreamG8 + "\nreset refs/heads/master\n\ncommit refs/heads/master\ncommitter t <t@t> 1709287500 +0000\ndata 7\norphan\nM 100644 inline o.txt\ndata 2\no\n"
	b47e2dImport(t, r, stream, &FastImportOptions{Force: true})
 
	c := b47e2dCommit(t, r, b47e2dRef(t, r, "refs/heads/master"))
	require.Equal(t, 0, c.NumParents())
	require.Equal(t, "orphan\n", c.Message)
	require.Equal(t, "o\n", b47e2dFile(t, c, "o.txt"))
	_, err := c.File("f")
	require.Error(t, err)
}
TestFastImportB47e2dMarksExport
unchanged
go
func TestFastImportB47e2dMarksExport(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	var marks bytes.Buffer
	b47e2dImport(t, r, b47e2dStreamG1, &FastImportOptions{ExportMarks: &marks})
 
	require.Equal(t,
		":1 4a58007052a65fbc2fc3f910f2855f45a4058e74\n:2 9e0e0679776bffc4ed1e980c6f6c308c700f2ac6\n",
		marks.String())
}
TestFastImportB47e2dMarksImportIncremental
unchanged
go
func TestFastImportB47e2dMarksImportIncremental(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	var marks bytes.Buffer
	b47e2dImport(t, r, b47e2dStreamG1, &FastImportOptions{ExportMarks: &marks})
 
	var marks2 bytes.Buffer
	res := b47e2dImport(t, r, b47e2dStreamG14, &FastImportOptions{ImportMarks: &marks, ExportMarks: &marks2})
 
	require.Equal(t, 1, res.Commits)
	require.Equal(t, "b46982696b8186df3b611d53622e69bf72e66e3d", b47e2dRef(t, r, "refs/heads/master").String())
	require.Contains(t, marks2.String(), ":3 b46982696b8186df3b611d53622e69bf72e66e3d\n")
	require.Contains(t, marks2.String(), ":1 4a58007052a65fbc2fc3f910f2855f45a4058e74\n")
}
TestFastImportB47e2dBadQuotedPathEscape
unchanged
go
func TestFastImportB47e2dBadQuotedPathEscape(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	stream := "blob\nmark :1\ndata 2\nx\n" +
		"commit refs/heads/master\ncommitter t <t@t> 1709287200 +0000\ndata 3\nc1\n" +
		"M 100644 :1 \"a\\qb.txt\"\n"
	_, err := r.FastImport(strings.NewReader(stream), &FastImportOptions{})
	require.Error(t, err)
	require.Equal(t, 9, b47e2dErrLine(t, err))
 
	_, refErr := r.Reference(plumbing.NewBranchReferenceName("master"), true)
	require.Error(t, refErr)
}
TestFastImportB47e2dCopyFileOntoDirectory
unchanged
go
func TestFastImportB47e2dCopyFileOntoDirectory(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	stream := "blob\nmark :1\ndata 2\na\n" +
		"commit refs/heads/master\ncommitter t <t@t> 1709287200 +0000\ndata 3\nc1\nM 100644 :1 top\nM 100644 :1 d/inner\n" +
		"commit refs/heads/master\ncommitter t <t@t> 1709287300 +0000\ndata 3\nc2\nC top d\n"
	b47e2dImport(t, r, stream, nil)
 
	c := b47e2dCommit(t, r, b47e2dRef(t, r, "refs/heads/master"))
	require.Equal(t, "a\n", b47e2dFile(t, c, "d"))
	_, err := c.File("d/inner")
	require.Error(t, err)
	require.Equal(t, "a\n", b47e2dFile(t, c, "top"))
}
TestFastImportB47e2dUnknownMarkFailsWithLine
unchanged
go
func TestFastImportB47e2dUnknownMarkFailsWithLine(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	_, err := r.FastImport(strings.NewReader(b47e2dStreamFail), &FastImportOptions{})
	require.Error(t, err)
 
	require.Equal(t, 19, b47e2dErrLine(t, err))
}
TestFastImportB47e2dFailureLeavesRefsUntouched
unchanged
go
func TestFastImportB47e2dFailureLeavesRefsUntouched(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	_, err := r.FastImport(strings.NewReader(b47e2dStreamFail), &FastImportOptions{})
	require.Error(t, err)
 
	b47e2dErrLine(t, err)
 
	_, err = r.Reference(plumbing.NewBranchReferenceName("master"), true)
	require.Error(t, err)
 
	iter, err := r.References()
	require.NoError(t, err)
	count := 0
Show 8 more lines
TestFastImportB47e2dCheckpointMakesRefsDurable
unchanged
go
func TestFastImportB47e2dCheckpointMakesRefsDurable(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	_, err := r.FastImport(strings.NewReader(b47e2dStreamCheckpoint), &FastImportOptions{})
	require.Error(t, err)
 
	require.Equal(t, "ba5a7ce38b514ecb6fc2d79a3c737fd9fc4c9c59", b47e2dRef(t, r, "refs/heads/master").String())
}
TestFastImportB47e2dExistingRefNotImplicitParent
unchanged
go
func TestFastImportB47e2dExistingRefNotImplicitParent(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	b47e2dImport(t, r, b47e2dStreamG1, nil)
 
	res := b47e2dImport(t, r, b47e2dStreamG15, nil)
	require.Equal(t, 1, res.Commits)
	require.Equal(t, []string{"refs/heads/master"}, res.SkippedRefs)
	require.Equal(t, "9e0e0679776bffc4ed1e980c6f6c308c700f2ac6", b47e2dRef(t, r, "refs/heads/master").String())
}
TestFastImportB47e2dForceUpdatesNonFastForward
unchanged
go
func TestFastImportB47e2dForceUpdatesNonFastForward(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	b47e2dImport(t, r, b47e2dStreamG1, nil)
 
	res := b47e2dImport(t, r, b47e2dStreamG15, &FastImportOptions{Force: true})
	require.Empty(t, res.SkippedRefs)
	require.Equal(t, "b309f5ba59e44b0f6c17b19dfb854db1f65c637c", b47e2dRef(t, r, "refs/heads/master").String())
 
	c := b47e2dCommit(t, r, b47e2dRef(t, r, "refs/heads/master"))
	require.Equal(t, 0, c.NumParents())
	require.Equal(t, "extra\n", b47e2dFile(t, c, "extra.txt"))
}
TestFastImportB47e2dFastForwardUpdateAllowed
unchanged
go
func TestFastImportB47e2dFastForwardUpdateAllowed(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	var marks bytes.Buffer
	b47e2dImport(t, r, b47e2dStreamG1, &FastImportOptions{ExportMarks: &marks})
 
	res := b47e2dImport(t, r, b47e2dStreamG14, &FastImportOptions{ImportMarks: &marks})
	require.Empty(t, res.SkippedRefs)
	require.Equal(t, "b46982696b8186df3b611d53622e69bf72e66e3d", b47e2dRef(t, r, "refs/heads/master").String())
}
TestFastImportB47e2dDoneStopsProcessing
unchanged
go
func TestFastImportB47e2dDoneStopsProcessing(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	stream := b47e2dStreamG1 + "\ndone\nthis is not a valid command\n"
	res := b47e2dImport(t, r, stream, nil)
 
	require.Equal(t, 1, res.Commits)
	require.Equal(t, "9e0e0679776bffc4ed1e980c6f6c308c700f2ac6", b47e2dRef(t, r, "refs/heads/master").String())
}
TestFastImportB47e2dProgressIgnored
unchanged
go
func TestFastImportB47e2dProgressIgnored(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	stream := "progress starting up\n\n" + b47e2dStreamG1 + "\nprogress all done\n"
	res := b47e2dImport(t, r, stream, nil)
 
	require.Equal(t, 1, res.Commits)
	require.Equal(t, "9e0e0679776bffc4ed1e980c6f6c308c700f2ac6", b47e2dRef(t, r, "refs/heads/master").String())
}
TestFastImportB47e2dRoundTripFastExportStream
unchanged
go
func TestFastImportB47e2dRoundTripFastExportStream(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	res := b47e2dImport(t, r, b47e2dStreamRich, nil)
 
	require.Equal(t, 7, res.Blobs)
	require.Equal(t, 5, res.Commits)
	require.Equal(t, 1, res.Tags)
	require.Equal(t, "8be7653b23602f89b443a5aac66ed4779b158293", b47e2dRef(t, r, "refs/heads/master").String())
	require.Equal(t, "3bfdcb8174f4eb70063e231b9a7d5bc201915556", b47e2dRef(t, r, "refs/heads/side").String())
	require.Equal(t, "e312f554cb083e8b59ec712abd224ca9560f43bf", b47e2dRef(t, r, "refs/tags/v1").String())
}
TestFastImportB47e2dFilesystemStorageSameHashes
unchanged
go
func TestFastImportB47e2dFilesystemStorageSameHashes(t *testing.T) {
	t.Parallel()
	dir := t.TempDir()
	r, err := PlainInit(dir, false)
	require.NoError(t, err)
 
	b47e2dImport(t, r, b47e2dStreamRich, nil)
	require.Equal(t, "8be7653b23602f89b443a5aac66ed4779b158293", b47e2dRef(t, r, "refs/heads/master").String())
	require.Equal(t, "e312f554cb083e8b59ec712abd224ca9560f43bf", b47e2dRef(t, r, "refs/tags/v1").String())
}
TestFastImportB47e2dWorktreeUntouched
unchanged
go
func TestFastImportB47e2dWorktreeUntouched(t *testing.T) {
	t.Parallel()
	dir := t.TempDir()
	r, err := PlainInit(dir, false)
	require.NoError(t, err)
 
	b47e2dImport(t, r, b47e2dStreamG1, nil)
 
	entries, err := os.ReadDir(dir)
	require.NoError(t, err)
	require.Len(t, entries, 1)
	require.Equal(t, ".git", entries[0].Name())
}
TestFastImportB47e2dLogWalksImportedHistory
unchanged
go
func TestFastImportB47e2dLogWalksImportedHistory(t *testing.T) {
	t.Parallel()
	r2 := b47e2dRepo(t)
	b47e2dImport(t, r2, b47e2dStreamG1, nil)
	head, err := r2.Reference(plumbing.NewBranchReferenceName("master"), true)
	require.NoError(t, err)
 
	iter, err := r2.Log(&LogOptions{From: head.Hash()})
	require.NoError(t, err)
	count := 0
	require.NoError(t, iter.ForEach(func(*object.Commit) error {
		count++
		return nil
	}))
Show 2 more lines
TestFastImportB47e2dBinaryDataInBlob
unchanged
go
func TestFastImportB47e2dBinaryDataInBlob(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	stream := "blob\nmark :1\ndata 5\na\x00b\xffc\ncommit refs/heads/master\ncommitter t <t@t> 1709287200 +0000\ndata 3\nc1\nM 100644 :1 bin\n"
	b47e2dImport(t, r, stream, nil)
 
	c := b47e2dCommit(t, r, b47e2dRef(t, r, "refs/heads/master"))
	require.Equal(t, "a\x00b\xffc", b47e2dFile(t, c, "bin"))
}
TestFastImportB47e2dCountedDataWithoutTrailingNewline
unchanged
go
func TestFastImportB47e2dCountedDataWithoutTrailingNewline(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	stream := "blob\nmark :1\ndata 3\nabc\ncommit refs/heads/master\ncommitter t <t@t> 1709287200 +0000\ndata 3\nc1\nM 100644 :1 f\n"
	b47e2dImport(t, r, stream, nil)
 
	c := b47e2dCommit(t, r, b47e2dRef(t, r, "refs/heads/master"))
	require.Equal(t, "abc", b47e2dFile(t, c, "f"))
}
TestFastImportB47e2dInlineData
unchanged
go
func TestFastImportB47e2dInlineData(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	stream := "commit refs/heads/master\ncommitter t <t@t> 1709287200 +0000\ndata 3\nc1\nM 100644 inline in.txt\ndata 7\ninline\n"
	b47e2dImport(t, r, stream, nil)
 
	c := b47e2dCommit(t, r, b47e2dRef(t, r, "refs/heads/master"))
	require.Equal(t, "inline\n", b47e2dFile(t, c, "in.txt"))
}
TestFastImportB47e2dDeleteSubtree
unchanged
go
func TestFastImportB47e2dDeleteSubtree(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	stream := b47e2dStreamG5 + "\ncommit refs/heads/master\ncommitter t <t@t> 1709287500 +0000\ndata 3\nc4\nM 100644 inline d/x\ndata 2\nx\nM 100644 inline d/y/z\ndata 2\nz\n\ncommit refs/heads/master\ncommitter t <t@t> 1709287600 +0000\ndata 3\nc5\nD d\n"
	b47e2dImport(t, r, stream, nil)
 
	c := b47e2dCommit(t, r, b47e2dRef(t, r, "refs/heads/master"))
	_, err := c.File("d/x")
	require.Error(t, err)
	_, err = c.File("d/y/z")
	require.Error(t, err)
	require.Equal(t, "b\n", b47e2dFile(t, c, "only.txt"))
}
TestFastImportB47e2dMissingCommitterError
unchanged
go
func TestFastImportB47e2dMissingCommitterError(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	stream := "commit refs/heads/master\ndata 3\nc1\n"
	_, err := r.FastImport(strings.NewReader(stream), &FastImportOptions{})
	require.Error(t, err)
 
	require.Equal(t, 2, b47e2dErrLine(t, err))
}
TestFastImportB47e2dUnsupportedModeError
unchanged
go
func TestFastImportB47e2dUnsupportedModeError(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	stream := "blob\nmark :1\ndata 2\nx\n\ncommit refs/heads/master\ncommitter t <t@t> 1709287200 +0000\ndata 3\nc1\nM 040000 :1 dir\n"
	_, err := r.FastImport(strings.NewReader(stream), &FastImportOptions{})
	require.Error(t, err)
 
	require.Equal(t, 10, b47e2dErrLine(t, err))
}
TestFastImportB47e2dUnknownCommandError
unchanged
go
func TestFastImportB47e2dUnknownCommandError(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	stream := "blob\nmark :1\ndata 2\nx\n\nfrobnicate now\n"
	_, err := r.FastImport(strings.NewReader(stream), &FastImportOptions{})
	require.Error(t, err)
 
	require.Equal(t, 6, b47e2dErrLine(t, err))
}
TestFastImportB47e2dUnterminatedDelimitedError
unchanged
go
func TestFastImportB47e2dUnterminatedDelimitedError(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	stream := "blob\nmark :1\ndata <<EOT\nnever closed\n"
	_, err := r.FastImport(strings.NewReader(stream), &FastImportOptions{})
	require.Error(t, err)
 
	b47e2dErrLine(t, err)
}
TestFastImportB47e2dBadDataLengthError
unchanged
go
func TestFastImportB47e2dBadDataLengthError(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	stream := "blob\nmark :1\ndata notanumber\n"
	_, err := r.FastImport(strings.NewReader(stream), &FastImportOptions{})
	require.Error(t, err)
 
	require.Equal(t, 3, b47e2dErrLine(t, err))
}
TestFastImportB47e2dMalformedIdentityError
unchanged
go
func TestFastImportB47e2dMalformedIdentityError(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	stream := "commit refs/heads/master\ncommitter broken identity line\ndata 3\nc1\n"
	_, err := r.FastImport(strings.NewReader(stream), &FastImportOptions{})
	require.Error(t, err)
 
	require.Equal(t, 2, b47e2dErrLine(t, err))
}
TestFastImportB47e2dUnknownRevisionError
unchanged
go
func TestFastImportB47e2dUnknownRevisionError(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	stream := "commit refs/heads/master\ncommitter t <t@t> 1709287200 +0000\ndata 3\nc1\nfrom refs/heads/nowhere\n"
	_, err := r.FastImport(strings.NewReader(stream), &FastImportOptions{})
	require.Error(t, err)
 
	b47e2dErrLine(t, err)
 
	_, refErr := r.Reference(plumbing.NewBranchReferenceName("master"), true)
	require.Error(t, refErr)
}
TestFastImportB47e2dTagFromExistingRef
unchanged
go
func TestFastImportB47e2dTagFromExistingRef(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	b47e2dImport(t, r, b47e2dStreamG1, nil)
 
	stream := "tag from-ref\nfrom refs/heads/master\ntagger t <t@t> 1709290800 +0000\ndata 3\ntm\n"
	res := b47e2dImport(t, r, stream, nil)
 
	require.Equal(t, 1, res.Tags)
	tag, err := r.TagObject(b47e2dRef(t, r, "refs/tags/from-ref"))
	require.NoError(t, err)
	require.Equal(t, "9e0e0679776bffc4ed1e980c6f6c308c700f2ac6", tag.Target.String())
}
TestFastImportB47e2dFromHashLiteral
unchanged
go
func TestFastImportB47e2dFromHashLiteral(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	b47e2dImport(t, r, b47e2dStreamG1, nil)
 
	stream := "commit refs/heads/other\ncommitter t <t@t> 1709287300 +0000\ndata 3\nc2\nfrom 9e0e0679776bffc4ed1e980c6f6c308c700f2ac6\nM 100644 inline n.txt\ndata 2\nn\n"
	b47e2dImport(t, r, stream, nil)
 
	c := b47e2dCommit(t, r, b47e2dRef(t, r, "refs/heads/other"))
	require.Len(t, c.ParentHashes, 1)
	require.Equal(t, "9e0e0679776bffc4ed1e980c6f6c308c700f2ac6", c.ParentHashes[0].String())
	require.Equal(t, "alpha\n", b47e2dFile(t, c, "a.txt"))
	require.Equal(t, "n\n", b47e2dFile(t, c, "n.txt"))
}
TestFastImportB47e2dModifyByFullBlobHash
unchanged
go
func TestFastImportB47e2dModifyByFullBlobHash(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	stream := "blob\nmark :1\ndata 2\na\n" +
		"commit refs/heads/master\ncommitter t <t@t> 1709287200 +0000\ndata 3\nc1\nM 100644 :1 base\n" +
		"commit refs/heads/master\ncommitter t <t@t> 1709287300 +0000\ndata 3\nc2\nM 100644 78981922613b2afb6025042ff6bd878ac1994e85 byhash\n"
	b47e2dImport(t, r, stream, nil)
 
	c := b47e2dCommit(t, r, b47e2dRef(t, r, "refs/heads/master"))
	require.Equal(t, "a\n", b47e2dFile(t, c, "base"))
	require.Equal(t, "a\n", b47e2dFile(t, c, "byhash"))
}
TestFastImportB47e2dResetFromRefName
unchanged
go
func TestFastImportB47e2dResetFromRefName(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	b47e2dImport(t, r, b47e2dStreamG1, nil)
 
	stream := "reset refs/heads/copy\nfrom refs/heads/master\n"
	b47e2dImport(t, r, stream, nil)
 
	require.Equal(t, b47e2dRef(t, r, "refs/heads/master"), b47e2dRef(t, r, "refs/heads/copy"))
}
TestFastImportB47e2dMergeFromRefName
unchanged
go
func TestFastImportB47e2dMergeFromRefName(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	stream := "blob\nmark :1\ndata 2\na\n" +
		"commit refs/heads/main\ncommitter t <t@t> 1709287200 +0000\ndata 3\nc1\nM 100644 :1 f1\n" +
		"commit refs/heads/topic\ncommitter t <t@t> 1709287300 +0000\ndata 3\nc2\nfrom refs/heads/main\nM 100644 :1 f2\n" +
		"commit refs/heads/main\ncommitter t <t@t> 1709287400 +0000\ndata 3\nc3\nmerge refs/heads/topic\nM 100644 :1 f3\n"
	b47e2dImport(t, r, stream, nil)
 
	topic := b47e2dRef(t, r, "refs/heads/topic")
	c1 := b47e2dCommit(t, r, topic).ParentHashes[0]
 
	c3 := b47e2dCommit(t, r, b47e2dRef(t, r, "refs/heads/main"))
	require.Len(t, c3.ParentHashes, 2)
Show 3 more lines
TestFastImportB47e2dTagMarkReferenced
unchanged
go
func TestFastImportB47e2dTagMarkReferenced(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	var marks bytes.Buffer
	stream := "blob\nmark :1\ndata 2\nx\n" +
		"commit refs/heads/master\nmark :2\ncommitter t <t@t> 1709287200 +0000\ndata 3\nc1\nM 100644 :1 f\n" +
		"tag v1\nmark :3\nfrom :2\ntagger t <t@t> 1709290800 +0000\ndata 3\ntm\n"
	b47e2dImport(t, r, stream, &FastImportOptions{ExportMarks: &marks})
 
	tagHash := b47e2dRef(t, r, "refs/tags/v1")
	require.Contains(t, marks.String(), ":3 "+tagHash.String())
}
TestFastImportB47e2dInlineBlobsCounted
unchanged
go
func TestFastImportB47e2dInlineBlobsCounted(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	stream := "commit refs/heads/master\ncommitter t <t@t> 1709287200 +0000\ndata 3\nc1\n" +
		"M 100644 inline a\ndata 2\na\n" +
		"M 100644 inline b\ndata 2\nb\n"
	res := b47e2dImport(t, r, stream, nil)
 
	require.Equal(t, 2, res.Blobs)
	require.Equal(t, 1, res.Commits)
}
TestFastImportB47e2dResetToBadRevisionErrors
unchanged
go
func TestFastImportB47e2dResetToBadRevisionErrors(t *testing.T) {
	t.Parallel()
	good := b47e2dRepo(t)
	b47e2dImport(t, good, b47e2dStreamG1, nil)
	b47e2dImport(t, good, "reset refs/heads/ok\nfrom refs/heads/master\n", nil)
	require.Equal(t, b47e2dRef(t, good, "refs/heads/master"), b47e2dRef(t, good, "refs/heads/ok"))
 
	r := b47e2dRepo(t)
	stream := "blob\nmark :1\ndata 2\nx\n" +
		"reset refs/heads/broken\nfrom :1\n"
	_, err := r.FastImport(strings.NewReader(stream), &FastImportOptions{})
	require.Error(t, err)
}
TestFastImportB47e2dGitlinkToAbsentCommit
unchanged
go
func TestFastImportB47e2dGitlinkToAbsentCommit(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	stream := "blob\nmark :1\ndata 2\nx\n" +
		"commit refs/heads/master\ncommitter t <t@t> 1709287200 +0000\ndata 3\nc1\n" +
		"M 100644 :1 f\n" +
		"M 160000 deadbeefdeadbeefdeadbeefdeadbeefdeadbeef sub\n"
	res := b47e2dImport(t, r, stream, nil)
	require.Equal(t, 1, res.Commits)
 
	c := b47e2dCommit(t, r, b47e2dRef(t, r, "refs/heads/master"))
	tree, err := c.Tree()
	require.NoError(t, err)
	sub, err := tree.FindEntry("sub")
Show 4 more lines
TestFastImportB47e2dBareResetPreservesRef
unchanged
go
func TestFastImportB47e2dBareResetPreservesRef(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	b47e2dImport(t, r, b47e2dStreamG1, nil)
	before := b47e2dRef(t, r, "refs/heads/master")
 
	b47e2dImport(t, r, "reset refs/heads/master\n", nil)
 
	after := b47e2dRef(t, r, "refs/heads/master")
	require.Equal(t, before, after)
}
TestFastImportB47e2dFromAfterActionFails
unchanged
go
func TestFastImportB47e2dFromAfterActionFails(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	stream := "blob\nmark :1\ndata 2\nx\n" +
		"commit refs/heads/base\nmark :2\ncommitter t <t@t> 1709287200 +0000\ndata 3\nc1\nM 100644 :1 base\n" +
		"commit refs/heads/master\ncommitter t <t@t> 1709287300 +0000\ndata 3\nc2\n" +
		"M 100644 :1 f\nfrom :2\n"
	_, err := r.FastImport(strings.NewReader(stream), &FastImportOptions{})
	require.Error(t, err)
	b47e2dErrLine(t, err)
 
	_, refErr := r.Reference(plumbing.NewBranchReferenceName("master"), true)
	require.Error(t, refErr)
}
TestFastImportB47e2dMergeAfterActionFails
unchanged
go
func TestFastImportB47e2dMergeAfterActionFails(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	stream := "blob\nmark :1\ndata 2\nx\n" +
		"commit refs/heads/a\ncommitter t <t@t> 1709287200 +0000\ndata 3\nc1\nM 100644 :1 f\n" +
		"commit refs/heads/master\ncommitter t <t@t> 1709287300 +0000\ndata 3\nc2\nM 100644 :1 g\nmerge refs/heads/a\n"
	_, err := r.FastImport(strings.NewReader(stream), &FastImportOptions{})
	require.Error(t, err)
	b47e2dErrLine(t, err)
}
TestFastImportB47e2dEmptyMessageNoTerminator
unchanged
go
func TestFastImportB47e2dEmptyMessageNoTerminator(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	stream := "blob\nmark :1\ndata 2\nx\n" +
		"commit refs/heads/master\ncommitter t <t@t> 1709287200 +0000\ndata 0\nM 100644 :1 f\n"
	b47e2dImport(t, r, stream, nil)
 
	c := b47e2dCommit(t, r, b47e2dRef(t, r, "refs/heads/master"))
	require.Equal(t, "", c.Message)
	require.Equal(t, "x\n", b47e2dFile(t, c, "f"))
}
TestFastImportB47e2dCommitEncodingHeader
unchanged
go
func TestFastImportB47e2dCommitEncodingHeader(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	stream := "blob\nmark :1\ndata 2\nx\n" +
		"commit refs/heads/master\ncommitter t <t@t> 1709287200 +0000\nencoding ISO-8859-1\ndata 3\nc1\nM 100644 :1 f\n"
	b47e2dImport(t, r, stream, nil)
 
	require.Equal(t, "e1bbef4568118f4fce7d2abb8bfc353f63fc8198", b47e2dRef(t, r, "refs/heads/master").String())
	c := b47e2dCommit(t, r, b47e2dRef(t, r, "refs/heads/master"))
	require.Equal(t, object.MessageEncoding("ISO-8859-1"), c.Encoding)
}
TestFastImportB47e2dResetFromFullHash
unchanged
go
func TestFastImportB47e2dResetFromFullHash(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	b47e2dImport(t, r, b47e2dStreamG1, nil)
	h := b47e2dRef(t, r, "refs/heads/master")
 
	b47e2dImport(t, r, "reset refs/heads/copy\nfrom "+h.String()+"\n", nil)
	require.Equal(t, h, b47e2dRef(t, r, "refs/heads/copy"))
}
TestFastImportB47e2dTagFromFullHash
unchanged
go
func TestFastImportB47e2dTagFromFullHash(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	b47e2dImport(t, r, b47e2dStreamG1, nil)
	h := b47e2dRef(t, r, "refs/heads/master")
 
	stream := "tag fh\nfrom " + h.String() + "\ntagger t <t@t> 1709290800 +0000\ndata 3\ntm\n"
	b47e2dImport(t, r, stream, nil)
 
	tag, err := r.TagObject(b47e2dRef(t, r, "refs/tags/fh"))
	require.NoError(t, err)
	require.Equal(t, h, tag.Target)
}
TestFastImportB47e2dMergeFromFullHash
unchanged
go
func TestFastImportB47e2dMergeFromFullHash(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	b47e2dImport(t, r, b47e2dStreamG1, nil)
	h := b47e2dRef(t, r, "refs/heads/master")
 
	stream := "blob\nmark :1\ndata 2\ny\n" +
		"commit refs/heads/topic\ncommitter t <t@t> 1709287300 +0000\ndata 3\nc2\n" +
		"merge " + h.String() + "\nM 100644 :1 g\n"
	b47e2dImport(t, r, stream, nil)
 
	c := b47e2dCommit(t, r, b47e2dRef(t, r, "refs/heads/topic"))
	require.Len(t, c.ParentHashes, 1)
	require.Equal(t, h, c.ParentHashes[0])
Show 1 more lines
TestFastImportB47e2dCopyIntoFileAncestor
unchanged
go
func TestFastImportB47e2dCopyIntoFileAncestor(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	stream := "blob\nmark :1\ndata 2\nx\n" +
		"commit refs/heads/master\ncommitter t <t@t> 1709287200 +0000\ndata 3\nc1\nM 100644 :1 a\nM 100644 :1 x\n" +
		"commit refs/heads/master\ncommitter t <t@t> 1709287300 +0000\ndata 3\nc2\nC x a/b\n"
	b47e2dImport(t, r, stream, nil)
 
	require.Equal(t, "cdb19ff20b9ff484e34e4681e4253e39120a2a41", b47e2dRef(t, r, "refs/heads/master").String())
	c := b47e2dCommit(t, r, b47e2dRef(t, r, "refs/heads/master"))
	require.Equal(t, "x\n", b47e2dFile(t, c, "a/b"))
	_, err := c.File("a")
	require.Error(t, err)
}
TestFastImportB47e2dRenameIntoFileAncestor
unchanged
go
func TestFastImportB47e2dRenameIntoFileAncestor(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	stream := "blob\nmark :1\ndata 2\nx\n" +
		"commit refs/heads/master\ncommitter t <t@t> 1709287200 +0000\ndata 3\nc1\nM 100644 :1 a\nM 100644 :1 x\n" +
		"commit refs/heads/master\ncommitter t <t@t> 1709287300 +0000\ndata 3\nc2\nR x a/b\n"
	b47e2dImport(t, r, stream, nil)
 
	require.Equal(t, "a526df5448b7b5ae92b36cb73011a11a76a6006e", b47e2dRef(t, r, "refs/heads/master").String())
	c := b47e2dCommit(t, r, b47e2dRef(t, r, "refs/heads/master"))
	require.Equal(t, "x\n", b47e2dFile(t, c, "a/b"))
	_, aerr := c.File("a")
	require.Error(t, aerr)
	_, xerr := c.File("x")
Show 2 more lines
TestFastImportB47e2dBareResetCancelsPendingCommit
unchanged
go
func TestFastImportB47e2dBareResetCancelsPendingCommit(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	stream := "blob\nmark :1\ndata 2\nx\n" +
		"commit refs/heads/topic\ncommitter t <t@t> 1709287200 +0000\ndata 3\nc1\nM 100644 :1 f\n" +
		"reset refs/heads/topic\n"
	b47e2dImport(t, r, stream, nil)
 
	_, err := r.Reference(plumbing.NewBranchReferenceName("topic"), true)
	require.Error(t, err)
}
TestFastImportB47e2dEmptyStream
unchanged
go
func TestFastImportB47e2dEmptyStream(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	res, err := r.FastImport(strings.NewReader(""), &FastImportOptions{})
	require.NoError(t, err)
	require.Equal(t, 0, res.Blobs+res.Commits+res.Tags)
}
TestFastImportB47e2dCommentsAndBlankLinesIgnored
unchanged
go
func TestFastImportB47e2dCommentsAndBlankLinesIgnored(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	stream := "# leading comment\n\n" + b47e2dStreamG1
	res := b47e2dImport(t, r, stream, nil)
	require.Equal(t, 1, res.Commits)
	require.Equal(t, "9e0e0679776bffc4ed1e980c6f6c308c700f2ac6", b47e2dRef(t, r, "refs/heads/master").String())
}
TestFastImportB47e2dDirectoryRename
unchanged
go
func TestFastImportB47e2dDirectoryRename(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	stream := b47e2dStreamG5 + "\ncommit refs/heads/master\ncommitter t <t@t> 1709287700 +0000\ndata 3\nc6\nM 100644 inline nest/a/one\ndata 2\n1\nM 100644 inline nest/a/b/two\ndata 2\n2\n\ncommit refs/heads/master\ncommitter t <t@t> 1709287800 +0000\ndata 3\nc7\nR nest moved-nest\n"
	b47e2dImport(t, r, stream, nil)
 
	c := b47e2dCommit(t, r, b47e2dRef(t, r, "refs/heads/master"))
	require.Equal(t, "1\n", b47e2dFile(t, c, "moved-nest/a/one"))
	require.Equal(t, "2\n", b47e2dFile(t, c, "moved-nest/a/b/two"))
	_, err := c.File("nest/a/one")
	require.Error(t, err)
}
 
const b47e2dBaseAF = "blob\nmark :1\ndata 2\nx\n" +
Show 1 more lines
TestFastImportB47e2dFromAfterMergeRejected
unchanged
go
func TestFastImportB47e2dFromAfterMergeRejected(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	err := b47e2dFail(t, r, b47e2dBaseAF+
		"commit refs/heads/m\ncommitter t <t@t> 2 +0000\ndata 3\nc2\nmerge :2\nfrom :2\nM 100644 :1 z\n")
	b47e2dErrLine(t, err)
}
TestFastImportB47e2dTruncatedCountedData
unchanged
go
func TestFastImportB47e2dTruncatedCountedData(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	err := b47e2dFail(t, r, "blob\nmark :1\ndata 100\nshort\n")
	b47e2dErrLine(t, err)
}
TestFastImportB47e2dCommentInsideCommitActions
unchanged
go
func TestFastImportB47e2dCommentInsideCommitActions(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	b47e2dImport(t, r, b47e2dBaseAF+
		"commit refs/heads/m\ncommitter t <t@t> 2 +0000\ndata 3\nc2\nfrom :2\nM 100644 :1 p\n#a comment\nM 100644 :1 q\n", nil)
	c := b47e2dCommit(t, r, b47e2dRef(t, r, "refs/heads/m"))
	require.Equal(t, "x\n", b47e2dFile(t, c, "p"))
	require.Equal(t, "x\n", b47e2dFile(t, c, "q"))
}
TestFastImportB47e2dInvalidTimezoneRejected
unchanged
go
func TestFastImportB47e2dInvalidTimezoneRejected(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	err := b47e2dFail(t, r, "blob\nmark :1\ndata 2\nx\ncommit refs/heads/m\ncommitter t <t@t> 1 +2460\ndata 3\nc1\nM 100644 :1 f\n")
	b47e2dErrLine(t, err)
}
TestFastImportB47e2dUppercaseHashRevision
unchanged
go
func TestFastImportB47e2dUppercaseHashRevision(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	b47e2dImport(t, r, b47e2dBaseAF, nil)
	h := b47e2dRef(t, r, "refs/heads/base")
	upper := strings.ToUpper(h.String())
	b47e2dImport(t, r, "reset refs/heads/copy\nfrom "+upper+"\n", nil)
	require.Equal(t, h, b47e2dRef(t, r, "refs/heads/copy"))
}
TestFastImportB47e2dGitlinkRejectsInline
unchanged
go
func TestFastImportB47e2dGitlinkRejectsInline(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	err := b47e2dFail(t, r, "commit refs/heads/m\ncommitter t <t@t> 1 +0000\ndata 3\nc1\nM 160000 inline sub\ndata 2\nx\n")
	b47e2dErrLine(t, err)
}
TestFastImportB47e2dGitlinkRejectsBlobMark
unchanged
go
func TestFastImportB47e2dGitlinkRejectsBlobMark(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	err := b47e2dFail(t, r, b47e2dBaseAF+
		"commit refs/heads/m\ncommitter t <t@t> 2 +0000\ndata 3\nc2\nM 160000 :1 sub\n")
	b47e2dErrLine(t, err)
}
TestFastImportB47e2dRegularFileRejectsCommitMark
unchanged
go
func TestFastImportB47e2dRegularFileRejectsCommitMark(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	err := b47e2dFail(t, r, b47e2dBaseAF+
		"commit refs/heads/m\ncommitter t <t@t> 2 +0000\ndata 3\nc2\nM 100644 :2 f\n")
	b47e2dErrLine(t, err)
}
TestFastImportB47e2dSymlinkRejectsMissingObject
unchanged
go
func TestFastImportB47e2dSymlinkRejectsMissingObject(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	err := b47e2dFail(t, r, "commit refs/heads/m\ncommitter t <t@t> 1 +0000\ndata 3\nc1\nM 120000 0123456789012345678901234567890123456789 link\n")
	b47e2dErrLine(t, err)
}
TestFastImportB47e2dPeelsAnnotatedTagInReset
unchanged
go
func TestFastImportB47e2dPeelsAnnotatedTagInReset(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	b47e2dImport(t, r, b47e2dBaseAF+
		"tag v1\nfrom :2\ntagger t <t@t> 1 +0000\ndata 2\nm\n", nil)
	base := b47e2dRef(t, r, "refs/heads/base")
 
	b47e2dImport(t, r, "reset refs/heads/ft\nfrom refs/tags/v1\n", nil)
	require.Equal(t, base, b47e2dRef(t, r, "refs/heads/ft"))
}
TestFastImportB47e2dPeelsAnnotatedTagRefInMerge
unchanged
go
func TestFastImportB47e2dPeelsAnnotatedTagRefInMerge(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	b47e2dImport(t, r, b47e2dBaseAF+
		"tag v1\nfrom :2\ntagger t <t@t> 1 +0000\ndata 2\nm\n", nil)
	baseHash := b47e2dRef(t, r, "refs/heads/base")
	b47e2dImport(t, r, "blob\nmark :1\ndata 2\ny\n"+
		"commit refs/heads/topic\ncommitter t <t@t> 2 +0000\ndata 3\nc2\nmerge refs/tags/v1\nM 100644 :1 g\n", nil)
	c := b47e2dCommit(t, r, b47e2dRef(t, r, "refs/heads/topic"))
	require.Len(t, c.ParentHashes, 1)
	require.Equal(t, baseHash, c.ParentHashes[0])
}
TestFastImportB47e2dRenameToSelfPreserves
unchanged
go
func TestFastImportB47e2dRenameToSelfPreserves(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	b47e2dImport(t, r, b47e2dBaseAF+
		"commit refs/heads/base\ncommitter t <t@t> 2 +0000\ndata 3\nc2\nfrom :2\nR a a\n", nil)
	c := b47e2dCommit(t, r, b47e2dRef(t, r, "refs/heads/base"))
	require.Equal(t, "x\n", b47e2dFile(t, c, "a"))
}
TestFastImportB47e2dRenameIntoOwnDescendant
unchanged
go
func TestFastImportB47e2dRenameIntoOwnDescendant(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	b47e2dImport(t, r, b47e2dBaseAF+
		"commit refs/heads/base\ncommitter t <t@t> 2 +0000\ndata 3\nc2\nfrom :2\nR a a/b\n", nil)
	c := b47e2dCommit(t, r, b47e2dRef(t, r, "refs/heads/base"))
	require.Equal(t, "x\n", b47e2dFile(t, c, "a/b"))
	_, err := c.File("a")
	require.Error(t, err)
}
TestFastImportB47e2dRenameDirIntoSubdir
unchanged
go
func TestFastImportB47e2dRenameDirIntoSubdir(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	stream := "blob\nmark :1\ndata 2\nx\n" +
		"commit refs/heads/m\nmark :2\ncommitter t <t@t> 1 +0000\ndata 3\nc1\nM 100644 :1 dir/f\nM 100644 :1 dir/g\n" +
		"commit refs/heads/m\ncommitter t <t@t> 2 +0000\ndata 3\nc2\nfrom :2\nR dir dir/sub\n"
	b47e2dImport(t, r, stream, nil)
	c := b47e2dCommit(t, r, b47e2dRef(t, r, "refs/heads/m"))
	require.Equal(t, "x\n", b47e2dFile(t, c, "dir/sub/f"))
	require.Equal(t, "x\n", b47e2dFile(t, c, "dir/sub/g"))
}
TestFastImportB47e2dInvalidRefNameRejected
unchanged
go
func TestFastImportB47e2dInvalidRefNameRejected(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	err := b47e2dFail(t, r, b47e2dBaseAF+
		"commit refs/heads/..bad\ncommitter t <t@t> 2 +0000\ndata 3\nc2\nfrom :2\n")
	b47e2dErrLine(t, err)
}
TestFastImportB47e2dExistingNonCommitRefUpdates
unchanged
go
func TestFastImportB47e2dExistingNonCommitRefUpdates(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	b47e2dImport(t, r, b47e2dBaseAF+
		"tag v1\nfrom :2\ntagger t <t@t> 1 +0000\ndata 2\nm\n", nil)
	tagHash := b47e2dRef(t, r, "refs/tags/v1")
	require.NoError(t, r.Storer.SetReference(plumbing.NewHashReference("refs/heads/weird", tagHash)))
 
	res := b47e2dImport(t, r, "blob\nmark :1\ndata 2\ny\n"+
		"commit refs/heads/weird\ncommitter t <t@t> 2 +0000\ndata 3\nc2\nM 100644 :1 g\n", nil)
	require.Empty(t, res.SkippedRefs)
	require.NotEqual(t, tagHash, b47e2dRef(t, r, "refs/heads/weird"))
}
TestFastImportB47e2dBadMergeRevisionReportsMergeLine
unchanged
go
func TestFastImportB47e2dBadMergeRevisionReportsMergeLine(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	stream := b47e2dBaseAF +
		"commit refs/heads/m\ncommitter t <t@t> 2 +0000\ndata 3\nc2\nfrom :2\nmerge 0123456789012345678901234567890123456789\nM 100644 :1 z\n"
	err := b47e2dFail(t, r, stream)
	require.Equal(t, 16, b47e2dErrLine(t, err))
}
TestFastImportB47e2dCopyOfMissingPathReportsCopyLine
unchanged
go
func TestFastImportB47e2dCopyOfMissingPathReportsCopyLine(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	stream := b47e2dBaseAF +
		"commit refs/heads/base\ncommitter t <t@t> 2 +0000\ndata 3\nc2\nfrom :2\nC nope dst\n"
	err := b47e2dFail(t, r, stream)
	require.Equal(t, 16, b47e2dErrLine(t, err))
}
TestFastImportB47e2dEmptyCommitAtStreamEnd
unchanged
go
func TestFastImportB47e2dEmptyCommitAtStreamEnd(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	stream := "commit refs/heads/master\nmark :1\ncommitter t <t@t> 1 +0000\ndata 3\nc1\n" +
		"commit refs/heads/master\nmark :2\ncommitter t <t@t> 2 +0000\ndata 3\nc2\nfrom :1\n"
	res := b47e2dImport(t, r, stream, nil)
	require.Equal(t, 2, res.Commits)
	require.Equal(t, "0c2a3511fc80221f30b0b501d702dea7ce8b5052", b47e2dRef(t, r, "refs/heads/master").String())
	c := b47e2dCommit(t, r, b47e2dRef(t, r, "refs/heads/master"))
	require.Len(t, c.ParentHashes, 1)
}
TestFastImportB47e2dIgnorableLinesInCommandBodies
unchanged
go
func TestFastImportB47e2dIgnorableLinesInCommandBodies(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	stream := "#lead\n\nblob\n#in blob\n\nmark :1\ndata 2\nx\n" +
		"commit refs/heads/base\n#in commit header\n\nmark :2\ncommitter t <t@t> 1 +0000\ndata 3\nc1\nM 100644 :1 a\n" +
		"tag v1\n#in tag body\n\nfrom :2\ntagger t <t@t> 1 +0000\ndata 2\nm\n" +
		"reset refs/heads/copy\n#in reset body\n\nfrom :2\n"
	b47e2dImport(t, r, stream, nil)
 
	clean := b47e2dRepo(t)
	b47e2dImport(t, clean, "blob\nmark :1\ndata 2\nx\n"+
		"commit refs/heads/base\nmark :2\ncommitter t <t@t> 1 +0000\ndata 3\nc1\nM 100644 :1 a\n"+
		"tag v1\nfrom :2\ntagger t <t@t> 1 +0000\ndata 2\nm\n"+
		"reset refs/heads/copy\nfrom :2\n", nil)
Show 5 more lines
TestFastImportB47e2dProgressCommandIsATokenNotAPrefix
unchanged
go
func TestFastImportB47e2dProgressCommandIsATokenNotAPrefix(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	err := b47e2dFail(t, r, "progressive not a progress command\n")
	b47e2dErrLine(t, err)
}
TestFastImportB47e2dNegativeTimestampFidelity
unchanged
go
func TestFastImportB47e2dNegativeTimestampFidelity(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	b47e2dImport(t, r, "blob\nmark :1\ndata 2\nx\n"+
		"commit refs/heads/master\ncommitter t <t@t> -100 +0000\ndata 3\nc1\nM 100644 :1 f\n", nil)
	require.Equal(t, "0fcbe92797970f95501d529b5b4f3411a3d1033c", b47e2dRef(t, r, "refs/heads/master").String())
}
TestFastImportB47e2dNegativeZeroTimezoneFidelity
unchanged
go
func TestFastImportB47e2dNegativeZeroTimezoneFidelity(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	b47e2dImport(t, r, "blob\nmark :1\ndata 2\nx\n"+
		"commit refs/heads/master\ncommitter t <t@t> 1 -0000\ndata 3\nc1\nM 100644 :1 f\n", nil)
	require.Equal(t, "2f7eeb176bbd017b72bb025769a731929663705f", b47e2dRef(t, r, "refs/heads/master").String())
 
	plus := b47e2dRepo(t)
	b47e2dImport(t, plus, "blob\nmark :1\ndata 2\nx\n"+
		"commit refs/heads/master\ncommitter t <t@t> 1 +0000\ndata 3\nc1\nM 100644 :1 f\n", nil)
	require.Equal(t, "6f42b75db1260804c3ca5271c76c9caf2df3c198", b47e2dRef(t, plus, "refs/heads/master").String())
}
TestFastImportB47e2dTimezoneBoundary
unchanged
go
func TestFastImportB47e2dTimezoneBoundary(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	b47e2dImport(t, r, "blob\nmark :1\ndata 2\nx\n"+
		"commit refs/heads/ok\ncommitter t <t@t> 1 +1400\ndata 3\nc1\nM 100644 :1 f\n", nil)
	require.NotEqual(t, plumbing.ZeroHash, b47e2dRef(t, r, "refs/heads/ok"))
 
	for _, tz := range []string{"+1401", "+1430"} {
		bad := b47e2dRepo(t)
		err := b47e2dFail(t, bad, "blob\nmark :1\ndata 2\nx\n"+
			"commit refs/heads/m\ncommitter t <t@t> 1 "+tz+"\ndata 3\nc1\nM 100644 :1 f\n")
		b47e2dErrLine(t, err)
	}
}
TestFastImportB47e2dQuotedControlCharacterPath
unchanged
go
func TestFastImportB47e2dQuotedControlCharacterPath(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	b47e2dImport(t, r, "blob\nmark :1\ndata 2\nx\n"+
		"commit refs/heads/master\ncommitter t <t@t> 1 +0000\ndata 3\nc1\nM 100644 :1 \"tab\\there.txt\"\n", nil)
	require.Equal(t, "ff1c0e00ec9cb754b3cf5275b64fb72b3517baa8", b47e2dRef(t, r, "refs/heads/master").String())
 
	c := b47e2dCommit(t, r, b47e2dRef(t, r, "refs/heads/master"))
	tree, err := c.Tree()
	require.NoError(t, err)
	require.Len(t, tree.Entries, 1)
	require.Equal(t, "tab\there.txt", tree.Entries[0].Name)
}
TestFastImportB47e2dMalformedOctalEscapeRejected
unchanged
go
func TestFastImportB47e2dMalformedOctalEscapeRejected(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	err := b47e2dFail(t, r, "blob\nmark :1\ndata 2\nx\n"+
		"commit refs/heads/m\ncommitter t <t@t> 1 +0000\ndata 3\nc1\nM 100644 :1 \"bad\\9escape.txt\"\n")
	b47e2dErrLine(t, err)
}
TestFastImportB47e2dInvalidTagNameRejected
unchanged
go
func TestFastImportB47e2dInvalidTagNameRejected(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	err := b47e2dFail(t, r, b47e2dBaseAF+
		"tag ..bad\nfrom :2\ntagger t <t@t> 1 +0000\ndata 2\nm\n")
	b47e2dErrLine(t, err)
}
TestFastImportB47e2dGitlinkFullHashToBlobRejected
unchanged
go
func TestFastImportB47e2dGitlinkFullHashToBlobRejected(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	b47e2dImport(t, r, b47e2dBaseAF, nil)
	c := b47e2dCommit(t, r, b47e2dRef(t, r, "refs/heads/base"))
	tree, err := c.Tree()
	require.NoError(t, err)
	blob, err := tree.FindEntry("a")
	require.NoError(t, err)
 
	bad := b47e2dRepo(t)
	b47e2dImport(t, bad, b47e2dBaseAF, nil)
	e := b47e2dFail(t, bad, "commit refs/heads/m\ncommitter t <t@t> 2 +0000\ndata 3\nc2\n"+
		"M 160000 "+blob.Hash.String()+" sub\n")
Show 2 more lines
TestFastImportB47e2dCommitFromAnnotatedTagRef
unchanged
go
func TestFastImportB47e2dCommitFromAnnotatedTagRef(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	b47e2dImport(t, r, b47e2dBaseAF+
		"tag v1\nfrom :2\ntagger t <t@t> 1 +0000\ndata 2\nm\n", nil)
	base := b47e2dRef(t, r, "refs/heads/base")
 
	b47e2dImport(t, r, "blob\nmark :1\ndata 2\ny\n"+
		"commit refs/heads/topic\ncommitter t <t@t> 2 +0000\ndata 3\nc2\nfrom refs/tags/v1\nM 100644 :1 g\n", nil)
	c := b47e2dCommit(t, r, b47e2dRef(t, r, "refs/heads/topic"))
	require.Len(t, c.ParentHashes, 1)
	require.Equal(t, base, c.ParentHashes[0])
}
TestFastImportB47e2dBadResetRevisionReportsFromLine
unchanged
go
func TestFastImportB47e2dBadResetRevisionReportsFromLine(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	err := b47e2dFail(t, r, b47e2dBaseAF+
		"reset refs/heads/m\nfrom 0123456789012345678901234567890123456789\n")
	require.Equal(t, 12, b47e2dErrLine(t, err))
}
TestFastImportB47e2dBadTagRevisionReportsFromLine
unchanged
go
func TestFastImportB47e2dBadTagRevisionReportsFromLine(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	err := b47e2dFail(t, r, b47e2dBaseAF+
		"tag v1\nfrom 0123456789012345678901234567890123456789\ntagger t <t@t> 1 +0000\ndata 2\nm\n")
	require.Equal(t, 12, b47e2dErrLine(t, err))
}
TestFastImportB47e2dFailedRenameReportsRenameLine
unchanged
go
func TestFastImportB47e2dFailedRenameReportsRenameLine(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	err := b47e2dFail(t, r, b47e2dBaseAF+
		"commit refs/heads/base\ncommitter t <t@t> 2 +0000\ndata 3\nc2\nfrom :2\nR nope dst\n")
	require.Equal(t, 16, b47e2dErrLine(t, err))
}
TestFastImportB47e2dFailedStreamKeepsWrittenObjects
unchanged
go
func TestFastImportB47e2dFailedStreamKeepsWrittenObjects(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	stream := "blob\nmark :1\ndata 2\nx\n" +
		"commit refs/heads/master\nmark :2\ncommitter t <t@t> 1 +0000\ndata 3\nc1\nM 100644 :1 a\n" +
		"commit refs/heads/master\ncommitter t <t@t> 2 +0000\ndata 3\nc2\nfrom :2\nM 100644 :99 b\n"
	_, err := r.FastImport(strings.NewReader(stream), &FastImportOptions{})
	require.Error(t, err)
 
	_, refErr := r.Reference(plumbing.NewBranchReferenceName("master"), true)
	require.Error(t, refErr)
 
	clean := b47e2dRepo(t)
	b47e2dImport(t, clean, "blob\nmark :1\ndata 2\nx\n"+
Show 6 more lines
TestFastImportB47e2dTagRequiresTaggerAndMessage
unchanged
go
func TestFastImportB47e2dTagRequiresTaggerAndMessage(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	err := b47e2dFail(t, r, b47e2dBaseAF+"tag v1\nfrom :2\ndata 2\nm\n")
	b47e2dErrLine(t, err)
 
	r2 := b47e2dRepo(t)
	err2 := b47e2dFail(t, r2, b47e2dBaseAF+"tag v1\nfrom :2\ntagger t <t@t> 1 +0000\n")
	b47e2dErrLine(t, err2)
}
TestFastImportB47e2dProgressIgnoredInCommandBodies
unchanged
go
func TestFastImportB47e2dProgressIgnoredInCommandBodies(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	stream := "blob\nprogress in blob\nmark :1\ndata 2\nx\n" +
		"commit refs/heads/m\nprogress in commit header\nmark :2\ncommitter t <t@t> 1 +0000\ndata 3\nc1\n" +
		"M 100644 inline p\nprogress before data\ndata 2\ny\n" +
		"tag v1\nprogress in tag\nfrom :2\ntagger t <t@t> 1 +0000\ndata 2\nm\n" +
		"reset refs/heads/c\nprogress in reset\nfrom :2\n"
	b47e2dImport(t, r, stream, nil)
 
	clean := b47e2dRepo(t)
	b47e2dImport(t, clean, "blob\nmark :1\ndata 2\nx\n"+
		"commit refs/heads/m\nmark :2\ncommitter t <t@t> 1 +0000\ndata 3\nc1\n"+
		"M 100644 inline p\ndata 2\ny\n"+
Show 7 more lines
TestFastImportB47e2dTaggerIdentityFidelity
unchanged
go
func TestFastImportB47e2dTaggerIdentityFidelity(t *testing.T) {
	t.Parallel()
	base := "blob\nmark :1\ndata 2\nx\n" +
		"commit refs/heads/master\nmark :2\ncommitter t <t@t> 1 +0000\ndata 3\nc1\nM 100644 :1 f\n"
 
	neg := b47e2dRepo(t)
	b47e2dImport(t, neg, base+"tag v1\nfrom :2\ntagger t <t@t> 1 -0000\ndata 2\nm\n", nil)
	require.Equal(t, "778f799b7a22f502d59e19287bdeaed782e535bc", b47e2dRef(t, neg, "refs/tags/v1").String())
 
	negTS := b47e2dRepo(t)
	b47e2dImport(t, negTS, base+"tag v1\nfrom :2\ntagger t <t@t> -100 +0000\ndata 2\nm\n", nil)
	require.Equal(t, "d5cd1d5baffab7c5069846d01e94b85125148405", b47e2dRef(t, negTS, "refs/tags/v1").String())
}
TestFastImportB47e2dRejectsNonCanonicalPaths
unchanged
go
func TestFastImportB47e2dRejectsNonCanonicalPaths(t *testing.T) {
	t.Parallel()
	for _, bad := range []string{"a//b", "a/./b", "a/../b", "/a", "a/"} {
		r := b47e2dRepo(t)
		err := b47e2dFail(t, r, "blob\nmark :1\ndata 2\nx\n"+
			"commit refs/heads/m\ncommitter t <t@t> 1 +0000\ndata 3\nc1\nM 100644 :1 "+bad+"\n")
		require.Equal(t, 9, b47e2dErrLine(t, err), "path %q", bad)
	}
}
TestFastImportB47e2dRejectsNulAndOverflowEscapeInPath
unchanged
go
func TestFastImportB47e2dRejectsNulAndOverflowEscapeInPath(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	err := b47e2dFail(t, r, "blob\nmark :1\ndata 2\nx\n"+
		"commit refs/heads/m\ncommitter t <t@t> 1 +0000\ndata 3\nc1\nM 100644 :1 \"a\\000b\"\n")
	b47e2dErrLine(t, err)
 
	r2 := b47e2dRepo(t)
	err2 := b47e2dFail(t, r2, "blob\nmark :1\ndata 2\nx\n"+
		"commit refs/heads/m\ncommitter t <t@t> 1 +0000\ndata 3\nc1\nM 100644 :1 \"b\\400.txt\"\n")
	b47e2dErrLine(t, err2)
}
TestFastImportB47e2dNonCanonicalPathInDeleteAndRename
unchanged
go
func TestFastImportB47e2dNonCanonicalPathInDeleteAndRename(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	err := b47e2dFail(t, r, b47e2dBaseAF+
		"commit refs/heads/base\ncommitter t <t@t> 2 +0000\ndata 3\nc2\nfrom :2\nD a//b\n")
	require.Equal(t, 16, b47e2dErrLine(t, err))
 
	r2 := b47e2dRepo(t)
	err2 := b47e2dFail(t, r2, b47e2dBaseAF+
		"commit refs/heads/base\ncommitter t <t@t> 2 +0000\ndata 3\nc2\nfrom :2\nR a /a\n")
	require.Equal(t, 16, b47e2dErrLine(t, err2))
}
TestFastImportB47e2dEmptyFromRejected
unchanged
go
func TestFastImportB47e2dEmptyFromRejected(t *testing.T) {
	t.Parallel()
	r := b47e2dRepo(t)
	err := b47e2dFail(t, r, b47e2dBaseAF+
		"commit refs/heads/m\ncommitter t <t@t> 2 +0000\ndata 3\nc2\nfrom \nM 100644 :1 b\n")
	b47e2dErrLine(t, err)
 
	r2 := b47e2dRepo(t)
	err2 := b47e2dFail(t, r2, b47e2dBaseAF+"reset refs/heads/c\nfrom \n")
	b47e2dErrLine(t, err2)
}
TestFastImportB47e2dCountsDistinctObjectsOnly
unchanged
go
func TestFastImportB47e2dCountsDistinctObjectsOnly(t *testing.T) {
	t.Parallel()
	one := "blob\nmark :1\ndata 2\nx\n" +
		"commit refs/heads/m\ncommitter t <t@t> 1 +0000\ndata 3\nc1\nM 100644 :1 a\n"
 
	r := b47e2dRepo(t)
	res := b47e2dImport(t, r, "blob\nmark :1\ndata 2\nx\nblob\nmark :2\ndata 2\nx\n"+
		"commit refs/heads/m\ncommitter t <t@t> 1 +0000\ndata 3\nc1\nM 100644 :1 a\nM 100644 :2 b\n", nil)
	require.Equal(t, 1, res.Blobs)
 
	fresh := b47e2dRepo(t)
	first := b47e2dImport(t, fresh, one, nil)
	require.Equal(t, 1, first.Blobs)
	require.Equal(t, 1, first.Commits)
Show 5 more lines
fastimport_streams_b47e2d_test.go
unchanged
hunk
package git
 
const (
	b47e2dStreamG1 = `blob
mark :1
data 6
alpha
 
commit refs/heads/master
mark :2
author An Author <author@example.com> 1709287200 +0000
committer A Committer <committer@example.com> 1709290800 +0130
data 14
first subject
Show 330 more lines
fastimport_stub_b47e2d_test.go
unchanged
hunk
//go:build fastimport_b47e2d_stub
 
package git
 
import (
	"errors"
	"io"
)
 
type FastImportOptions struct {
	ImportMarks io.Reader
	ExportMarks io.Writer
	Force       bool
}
Show 20 more lines
test.sh
unchanged
hunk
#!/bin/bash
set -uo pipefail
 
usage() {
    echo "usage: $0 --output_path <path> (base|new)" >&2
    exit 2
}
 
OUTPUT_PATH=""
MODE=""
while [ $# -gt 0 ]; do
    case "$1" in
        --output_path)
            [ $# -ge 2 ] || usage
Show 141 more lines
Hide carried-over tests

Report an issue

Help







3:


Shipd
/
olympus
Home
Events
Submissions
Payouts

587/600
2
Silver
Create
· $150–350
61
Verifier Completeness Audit
Generate Luau Declaration Files

Back to submission
Task description


Add a generateDeclarations(module) function to the analysis library that turns an already type-checked module into a standalone Luau declaration file. It returns a single string written in the same declaration syntax the analyzer already accepts as input, so feeding the result back through the definition-file loader reconstructs exactly the same types. The round trip from module to text back to types must be faithful. The function generateDeclarations, declared in Luau/DeclarationGenerator.h in namespace Luau, takes the checked Module and returns the file as a std::string.

The output covers the module's exported type aliases. Each exported alias appears as an export type entry, and any private alias in the module is emitted as well, written with a plain type entry and no export keyword so the file stands on its own. Aliases that refer to themselves, and aliases that refer to one another in a cycle, must be printed without expanding forever: a reference that reaches an alias prints that alias name rather than inlining its body again, so a recursive shape terminates.

Every kind of type that can appear in the surface serializes faithfully. This includes the primitive types, string and boolean literal types, the any, unknown, and never types, unions, and intersections. A union of some type with nil is written using the trailing question-mark optional form. Function types reproduce their parameters, variadic tail, and full result list, including the case of several results, and they re-emit their own generic parameters. Table types reproduce their fields in alphabetical order by name, distinguish read-only and write-only fields from ordinary ones, carry an indexer when present, stay correct when nested inside one another, and render an empty table when there are no fields.

Generic aliases re-emit their parameter list, and a parameter that carries a default value keeps that default in the output.

Extern types that the surface mentions are emitted as full extern type declarations, including an extends clause when the type has a parent, with the members it exposes. Because the aliases and values may reference these class types by name, the class declarations are placed ahead of everything that uses them so the file loads cleanly.

The module's returned value is reported too. Each field of the returned table becomes a declare entry giving that field a type, and a field whose value is a function with named parameters is written in the declare function form, spelling out the parameter names and the result, for example declare function make(x: number, y: number): Point. A function without usable parameter names still appears as a plain declared value. The declared value entries are likewise sorted alphabetically by field name.

The output is deterministic: aliases and fields are sorted alphabetically by name, so regenerating an unchanged module yields identical text. The analyzer exposes this through an --emit-declaration mode that prints each checked file's declaration to standard output, still reporting type errors on standard error and exiting with a non-zero status when an input has errors.
Incomplete
6 demonstrated
The audit demonstrated 6 gaps where a broken implementation could still pass the current tests. Review the proposed test patch below.

Audited the 94-test verifier, built and probed the reference oracle across primitive/literal, generic-pack, nested, recursive, returned-value, ordering, multi-file CLI, and error-stream cases. A composite implementation containing six plausible shortcuts passed all 94 original verifier tests; each shortcut diverged from the reference on a spec-grounded probe. I added six focused regression tests. The full replacement /var/artifacts/updated_test.patch applies to the pristine tree, and with the reference solution all 100 DeclarationGenerator tests pass (531 assertions).

Show less
Audited by Lyra
833.1s · 21 steps · 43 messages

Decision
4/4 validation checks passed

Accept as-is
Apply the proposed patch
Accept with edits
Edit on patch page

Bypass check
Keep your tests — the reviewer will be notified
Note for the reviewer (optional)
Context for whoever reviews this submission…
Submit decision
Requirements coverage

covered
gapped
Tier 1
10 covered · 7 gapped — by 6 gaps
Stated directly in the spec

Expose Luau::generateDeclarations for an already checked Module, returning the declaration file as std::string and declaring the API in Luau/DeclarationGenerator.h.
Produce standalone analyzer-accepted declaration syntax whose reload reconstructs the same types faithfully.
2 gaps
Emit every exported alias as export type and every private alias as non-exported type, including when no public alias/value refers to it.
1 gap
Terminate self-recursive and mutually recursive aliases by printing alias-name references rather than infinitely expanding bodies.
Faithfully serialize every surface type kind, including all primitives, string/boolean literals, any, unknown, never, unions, and intersections.
2 gaps
Serialize standalone nil faithfully, while rendering a union of exactly one non-nil type and nil with trailing optional syntax.
1 gap
Preserve function parameters, variadic tails, complete result packs including zero/multiple results, and function generic parameters.
Serialize table fields alphabetically; preserve ordinary/read-only/write-only access, indexers, nesting, and empty tables.
Re-emit generic alias type/type-pack parameter lists and preserve each default value.
Emit every mentioned extern type as a full extern declaration with parent extends clause and exposed members.
Place extern declarations, including dependencies and parents, before aliases or values that use them so loading succeeds.
Report every field of a returned table as a typed declare entry.
Use declare function only when all required parameter names are usable; if any parameter lacks a usable name, emit the function as a plain declared value.
1 gap
Sort returned-table declaration entries alphabetically by field name.
Make generation deterministic and sort aliases and fields alphabetically so repeated generation is byte-identical.
Provide --emit-declaration and print a declaration for every checked input file to stdout.
1 gap
In emit mode, keep type diagnostics on stderr and return nonzero when any input has errors.
1 gap
Tier 2
0 covered · 3 gapped — by 4 gaps
Entailed by interpretation — never stated outright

Escape all string-literal content needed to keep generated declaration text syntactically valid and preserve the original singleton value.
1 gap
Alternatives and fields are independent: serialization of one alias, returned field, or checked file must not suppress later entries.
2 gaps
Generated output must remain loadable for degenerate cases such as no exports, empty tables/packs, and partially named function signatures rather than crashing or emitting malformed syntax.
2 gaps
Demonstrated Gaps

Each gap is one plausible broken implementation that passes the entire original test suite while violating the linked requirements — proven by a probe the reference passes and the broken build fails.

Severity (Crash / Wrong result / Cosmetic) = what the uncaught flaw would do in the wild; plausibility (High / Medium / Low) = how likely someone would actually write it. Hover any pill for its exact meaning.

Wrong result
high plausibility
Demonstrated
Partially named returned functions can be misclassified as declare function and emitted malformed

Wrong result
high plausibility
Demonstrated
A module's private aliases can be dropped when it has no exported type surface

Wrong result
high plausibility
Demonstrated
Emit mode can silently stop after the first checked file

Wrong result
high plausibility
Demonstrated
Standalone nil can be serialized as any without detection

Wrong result
high plausibility
Demonstrated
Control characters in string singleton types can be emitted raw

Wrong result
high plausibility
Demonstrated
Emit-mode type errors can be written to stdout instead of stderr

Applies cleanly
Base tests pass
New tests fail on clean repo
Reference passes suite
Proposed tests (2)

Open patch & diff viewer
0 new · 1 modified · 1 carried over

DeclarationGenerator_ac60e8.test.cpp
modified
hunk
// This file is part of the Luau programming language and is licensed under MIT License; see LICENSE.txt for details
#include "Fixture.h"
#include "ClassFixture.h"
 
#include "Luau/DeclarationGenerator.h"
#include "Luau/ToString.h"
 
#include "doctest.h"
 
#include <cstdio>
#include <fstream>
 
using namespace Luau;
 
Show 1031 more lines
Show 1 carried-over tests

Report an issue

Help





4:



Shipd
/
olympus
Home
Events
Submissions
Payouts

449/450
Bronze
Create
· $150–350
20
Verifier Completeness Audit
Cell-level blame for Dolt tables

Back to submission
Task description


Add a table function, dolt_blame, that reports commit attribution at the level of individual cells rather than whole rows. Called with just a table name, it returns one row for every live row of that table: the primary key column or columns, and then, for every other column, four columns grouped together, the column's value followed by the commit that last changed that value, the committer who made it, and when. The attribution columns are named after the column with commit, committer, and commit date appended; the commit hash and the committer are both LONGTEXT strings, and the commit date is a DATETIME. Each attribution describes the last change to that one cell, not to the whole row.

The value shown for a cell is its current value at the blamed revision, while its attribution reaches back to whichever commit last set it. A value written when the row was inserted and never changed is attributed to that insert. A column added partway through the table's history is attributed, per row, to the commit that populated it, and for rows where it was never given a value both the value and its three attribution columns come back NULL. A schema-only change must not lose the trail: a value carried unchanged across a rename or a value-preserving type change of its own column is still attributed to the commit that last changed the value, not to the schema change.

A second argument chooses what to blame. With no second argument you blame the tip of the current branch. A single revision blames that revision, and both its rows and columns are taken as of it, so a row deleted afterwards is present again and a column added afterwards is absent. Two revisions separated by two dots blame a range: the returned rows and schema are taken as of the second revision, only commits reachable from the second but not the first contribute attribution, and a cell whose last change falls at or before the start of the range still shows its value but has NULL in its three attribution columns. When branches merge, a cell is attributed to the branch commit that set its value, not to a merge that only carried it forward unchanged.

Rows deleted at or before the blamed revision are not returned. A table with no primary key is rejected rather than blamed, with the error message "unable to generate blame for table without primary key". It is an error to name a table that does not exist at the blamed revision, to call the function with the wrong number of arguments, or to pass an argument that is not a string literal, such as a user variable. The function composes with filtering, ordering, and joins against other tables, and returns its rows ordered by primary key.

Test assumptions (error kinds): missing table sql.ErrTableNotFound; wrong argument count sql.ErrInvalidArgumentNumber; non-string literal sql.ErrInvalidArgumentDetails; non-literal argument dtablefunctions.ErrInvalidNonLiteralArgument; column absent at the pinned revision sql.ErrColumnNotFound.


Incomplete
2 demonstrated
The audit demonstrated 2 gaps where a broken implementation could still pass the current tests. Review the proposed test patch below.

Audited instruction.md, the 18 original dolt_blame script-test scenarios, and the reference implementation. The original verifier covers ordinary per-cell updates, inserted and explicit NULL values, added columns, rename and numeric type evolution, deletes, pinned revisions, ordinary two-dot ranges, composite keys, result schema/types, argument and table errors, ordering/LIMIT/filter/join composition, current-branch selection, and merge provenance. I ran the reference on additional adversarial cases: uncommitted working-set updates/inserts, a range containing change-then-revert to the start value, ADD COLUMN DEFAULT, delete/reinsert of the same key, a column dropped after a pinned revision, VARCHAR widening, a PK-only table, and an empty table. Two behaviors were genuine uncovered requirements. For each, a separate plausible shortcut implementation passed the full original TestOlympusBlameHiddenVerify suite but failed the reference-passing probe. I added two script scenarios covering those gaps. /var/artifacts/updated_test.patch is a full replacement patch, applies to the pristine checkout, and passes all 92 generated test cases with the reference solution (0 failures).

Show less
Audited by Lyra
447.8s · 18 steps · 37 messages

Decision
4/4 validation checks passed

Accept as-is
Apply the proposed patch
Accept with edits
Edit on patch page

Bypass check
Keep your tests — the reviewer will be notified
Note for the reviewer (optional)
Context for whoever reviews this submission…
Submit decision
Requirements coverage

covered
gapped
Tier 1
14 covered · 4 gapped — by 2 gaps
Stated directly in the spec

Provide a dolt_blame table function that attributes changes at individual-cell granularity rather than row granularity.
For a table-name-only call, return one result row per live table row, with all primary-key columns first and a four-column value/provenance group for every non-PK column.
Name attribution columns by appending commit, committer, and commit date to the value-column name; expose commit and committer as LONGTEXT and date as DATETIME.
Compute provenance independently for each cell, so changing one column or row does not steal another cell's attribution.
Return each cell's value at the blamed revision and attribute it to the latest commit that set that cell.
2 gaps
Attribute an inserted value that was never subsequently changed to the insertion commit, including an explicitly inserted NULL.
For a column added during history, attribute each populated cell to its population commit; a never-populated cell must have a NULL value and three NULL attribution fields.
Preserve prior value provenance across column rename and value-preserving type changes instead of attributing the schema-only commit.
Interpret an omitted revision as the tip commit of the currently checked-out branch, not another branch such as main.
1 gap
For a single revision, derive both rows and schema from that revision, resurrecting rows deleted later and excluding columns added later.
For a two-dot range, derive rows and schema from the second revision and allow attribution only from commits reachable from the second revision but not the first.
1 gap
In a range, retain a cell's endpoint value but return three NULL attribution fields when its latest change is at or before the range start.
1 gap
Across a merge, preserve attribution to the branch commit that set a carried-forward value rather than assigning it to a content-preserving merge.
Do not return rows deleted at or before the blamed revision.
Reject keyless tables with the exact specified error message.
Error for a table absent at the blamed revision, for argument counts outside one or two, and for any argument that is not a string literal, including variables.
Compose as a relational source with filtering, ordering, and joins, and emit rows in primary-key order without requiring an outer ORDER BY.
Use the specified error kinds for missing tables, wrong argument count, wrong literal type, non-literal expressions, and columns absent at a pinned revision.
Tier 2
1 covered · 2 gapped — by 2 gaps
Entailed by interpretation — never stated outright

An omitted revision must not substitute the mutable working root for the current branch tip; uncommitted row/value/schema changes are outside the blamed revision.
1 gap
In a range, a cell changed and then reverted after the start must be attributed to the later revert commit even when its endpoint value equals its start value; endpoint equality alone cannot imply NULL provenance.
1 gap
Handle degenerate valid tables uniformly: an empty table yields no rows, and a table with only PK columns still yields one PK-only result row per live row in PK order.
Demonstrated Gaps

Each gap is one plausible broken implementation that passes the entire original test suite while violating the linked requirements — proven by a probe the reference passes and the broken build fails.

Severity (Crash / Wrong result / Cosmetic) = what the uncaught flaw would do in the wild; plausibility (High / Medium / Low) = how likely someone would actually write it. Hover any pill for its exact meaning.

Wrong result
high plausibility
Demonstrated
Default invocation was not tested against uncommitted working-set changes

Wrong result
high plausibility
Demonstrated
Range tests missed changes that revert to the range-start value

Applies cleanly
Base tests pass
New tests fail on clean repo
Reference passes suite
Proposed tests (2)

Open patch & diff viewer
0 new · 0 modified · 2 carried over

Show 2 carried-over tests

Report an issue

Help
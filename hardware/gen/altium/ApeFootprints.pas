// ApeFootprints - what create_footprints_batch cannot do to lib/APE-SBC.PcbLib:
// replace existing footprints and set per-pad paste / solder mask expansion.
//
// Run from hardware/gen/footprints.py (run_fp, used by build.py footprints),
// which launches
//   X2.EXE -RScriptingSystem:RunScript(ProjectName="...\ApeFootprints.PrjScr"|ProcName="ApeFootprints>PadMasks")
// A script project of its own so that it cannot disturb ApeScripts or ApePlace.
//
// ape_fp_job.txt (the footprint spec, or the part of it that matters):
//   FPLIB|<full path of the .PcbLib>
//   REMOVE|<footprint>                 RemoveFootprints: delete every footprint of that name
//   FOOTPRINT|<footprint>|<description> PadMasks: the PADMASK lines below belong to it
//   PADMASK|<pad>|<paste mode>|<paste>|<mask mode>|<mask>
//       mode RULE (board rules), NONE (no paste / no mask opening) or MANUAL
//       (expansion in Altium units, 1 mil = 10000); every pad of that name
// Other record kinds are ignored. RemoveFootprints leaves the library unsaved
// (create_footprints_batch refills it next); PadMasks saves it.

const
    BRIDGE = 'C:\Users\Public\altium_mcp\';

var
    LogLines : TStringList;

procedure FpLog(Msg : String);
begin
    LogLines.Add(Msg);
    LogLines.SaveToFile(BRIDGE + 'ape_log.txt');
end;

procedure FpFinish(Json : String);
var
    R : TStringList;
begin
    FpLog('finish');
    R := TStringList.Create;
    R.Add(Json);
    R.SaveToFile(BRIDGE + 'ape_result.json');
    R.Free;
end;

// Pipe-delimited field, 0-based; '' past the end.
function Field(S : String; Index : Integer) : String;
var
    i, start, idx : Integer;
begin
    Result := '';
    idx := 0;
    start := 1;
    for i := 1 to Length(S) do
    begin
        if (S[i] = '|') then
        begin
            if (idx = Index) then
            begin
                Result := Copy(S, start, i - start);
                Exit;
            end;
            idx := idx + 1;
            start := i + 1;
        end;
    end;
    if (idx = Index) then
        Result := Copy(S, start, Length(S) - start + 1);
end;

function OpenLib(Path : String) : IPCB_Library;
var
    Doc : IServerDocument;
begin
    if Client.IsDocumentOpen(Path) then
        Doc := Client.GetDocumentByPath(Path)
    else
        Doc := Client.OpenDocument('PCBLIB', Path);
    Client.ShowDocument(Doc);
    Result := PCBServer.GetCurrentPCBLibrary;
end;

function ModeOf(S : String) : Integer;
begin
    if (S = 'NONE') then
        Result := eMaskExpansionMode_NoMask
    else if (S = 'MANUAL') then
        Result := eMaskExpansionMode_Manual
    else
        Result := eMaskExpansionMode_Rule;
end;

// ---------------------------------------------------- RemoveFootprints
procedure RemoveFootprints;
var
    L : TStringList;
    Lib : IPCB_Library;
    Comp : IPCB_LibComponent;
    Name : String;
    i, n, guard : Integer;
begin
    LogLines := TStringList.Create;
    FpLog('RemoveFootprints start');
    L := TStringList.Create;
    L.LoadFromFile(BRIDGE + 'ape_fp_job.txt');
    Lib := nil;
    n := 0;
    for i := 0 to L.Count - 1 do
    begin
        if (Field(L[i], 0) = 'FPLIB') then
        begin
            FpLog('open ' + Field(L[i], 1));
            Lib := OpenLib(Field(L[i], 1));
        end
        else if (Field(L[i], 0) = 'REMOVE') and (Lib <> nil) then
        begin
            Name := Field(L[i], 1);
            guard := 0;
            Comp := Lib.GetComponentByName(Name);
            while (Comp <> nil) and (guard < 10) and (Lib.ComponentCount > 1) do
            begin
                FpLog('remove ' + Name);
                Lib.RemoveComponent(Comp);
                Lib.Navigate_FirstComponent;
                n := n + 1;
                guard := guard + 1;
                Comp := Lib.GetComponentByName(Name);
            end;
        end;
    end;
    L.Free;
    if (Lib = nil) then
        FpFinish('{"success": false, "error": "no FPLIB record or the library did not open"}')
    else
        FpFinish('{"success": true, "removed": ' + IntToStr(n) + ', "footprints": ' + IntToStr(Lib.ComponentCount) + '}');
end;

// ------------------------------------------------------------ PadMasks
procedure PadMasks;
var
    L : TStringList;
    Lib : IPCB_Library;
    Comp : IPCB_LibComponent;
    Iter : IPCB_GroupIterator;
    Pad : IPCB_Pad;
    Doc : IServerDocument;
    Path, Missing : String;
    i, nPads, nSet : Integer;
begin
    LogLines := TStringList.Create;
    FpLog('PadMasks start');
    L := TStringList.Create;
    L.LoadFromFile(BRIDGE + 'ape_fp_job.txt');
    Lib := nil;
    Comp := nil;
    Path := '';
    Missing := '';
    nSet := 0;
    for i := 0 to L.Count - 1 do
    begin
        if (Field(L[i], 0) = 'FPLIB') then
        begin
            Path := Field(L[i], 1);
            FpLog('open ' + Path);
            Lib := OpenLib(Path);
        end
        else if (Field(L[i], 0) = 'FOOTPRINT') and (Lib <> nil) then
        begin
            Comp := Lib.GetComponentByName(Field(L[i], 1));
            if (Comp = nil) then
                Missing := Missing + ' ' + Field(L[i], 1);
        end
        else if (Field(L[i], 0) = 'PADMASK') and (Comp <> nil) then
        begin
            FpLog(Comp.Name + ' pad ' + Field(L[i], 1));
            nPads := 0;
            Iter := Comp.GroupIterator_Create;
            Iter.AddFilter_ObjectSet(MkSet(ePadObject));
            Pad := Iter.FirstPCBObject;
            while (Pad <> nil) do
            begin
                if (Pad.Name = Field(L[i], 1)) then
                begin
                    Pad.BeginModify;
                    Pad.PasteMaskExpansionMode := ModeOf(Field(L[i], 2));
                    if (Field(L[i], 2) = 'MANUAL') then
                        Pad.PasteMaskExpansion := StrToInt(Field(L[i], 3));
                    Pad.SolderMaskExpansionMode := ModeOf(Field(L[i], 4));
                    if (Field(L[i], 4) = 'MANUAL') then
                        Pad.SolderMaskExpansion := StrToInt(Field(L[i], 5));
                    Pad.EndModify;
                    nPads := nPads + 1;
                end;
                Pad := Iter.NextPCBObject;
            end;
            Comp.GroupIterator_Destroy(Iter);
            if (nPads = 0) then
                Missing := Missing + ' ' + Comp.Name + ':' + Field(L[i], 1);
            nSet := nSet + nPads;
        end;
    end;
    L.Free;
    if (Lib = nil) then
    begin
        FpFinish('{"success": false, "error": "no FPLIB record or the library did not open"}');
        Exit;
    end;
    FpLog('save');
    Doc := Client.GetDocumentByPath(Path);
    Doc.Modified := True;
    Doc.DoFileSave('');
    if (Missing = '') then
        FpFinish('{"success": true, "pads_set": ' + IntToStr(nSet) + ', "missing": ""}')
    else
        FpFinish('{"success": false, "pads_set": ' + IntToStr(nSet) + ', "missing": "' + Trim(Missing) + '"}');
end;

// ApeScripts - Altium automation for the APE-SBC schematic generator.
//
// Run from hardware/gen/build.py, which launches
//   X2.EXE -RScriptingSystem:RunScript(ProjectName="...\ApeScripts.PrjScr"|ProcName="ApeScripts>Xxx")
// Every procedure reads its input from C:\Users\Public\altium_mcp\, appends to
// ape_log.txt (flushed per line, so the last line shows where a crash happened)
// and writes ape_result.json when it finishes.
//
// This is a script project of its own rather than code pushed through the
// altium-mcp run_altium_script sandbox: that sandbox offers only a few scratch
// variables and no helpers, and an undeclared identifier there pauses the
// script in the debugger and blocks every later script run.

const
    BRIDGE = 'C:\Users\Public\altium_mcp\';

var
    LogLines : TStringList;

procedure ApeLog(Msg : String);
begin
    LogLines.Add(Msg);
    LogLines.SaveToFile(BRIDGE + 'ape_log.txt');
end;

procedure StartRun(Name : String);
begin
    LogLines := TStringList.Create;
    ApeLog(Name + ' start');
end;

procedure ApeFinish(Json : String);
var
    R : TStringList;
begin
    ApeLog('finish');
    R := TStringList.Create;
    R.Add(Json);
    R.SaveToFile(BRIDGE + 'ape_result.json');
    R.Free;
end;

// Pipe-delimited field, 0-based; '' past the end.
function PipeField(S : String; Index : Integer) : String;
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

function OpenApeDoc(Kind, Path : String) : IServerDocument;
begin
    if Client.IsDocumentOpen(Path) then
        Result := Client.GetDocumentByPath(Path)
    else
        Result := Client.OpenDocument(Kind, Path);
end;

procedure RegisterObj(Doc : ISch_Document; Obj : ISch_BasicContainer);
begin
    Doc.RegisterSchObjectInContainer(Obj);
    SchServer.RobotManager.SendMessage(Doc.I_ObjectAddress, c_BroadCast,
        SCHM_PrimitiveRegistration, Obj.I_ObjectAddress);
end;

// ---------------------------------------------------------------- Ping
procedure Ping;
begin
    StartRun('Ping');
    ApeFinish('{"success": true, "version": 11}');
end;

// ------------------------------------------------------------ SaveDocs
// ape_save_list.txt: KIND|full path per line.
procedure SaveDocs;
var
    L : TStringList;
    i, n : Integer;
    Doc : IServerDocument;
begin
    StartRun('SaveDocs');
    L := TStringList.Create;
    L.LoadFromFile(BRIDGE + 'ape_save_list.txt');
    n := 0;
    for i := 0 to L.Count - 1 do
        if (L[i] <> '') then
        begin
            ApeLog('saving ' + PipeField(L[i], 1));
            Doc := OpenApeDoc(PipeField(L[i], 0), PipeField(L[i], 1));
            if (Doc <> nil) then
            begin
                Doc.Modified := True;
                Doc.DoFileSave('');
                n := n + 1;
            end;
        end;
    L.Free;
    ApeFinish('{"success": true, "saved": ' + IntToStr(n) + '}');
end;

// ----------------------------------------------------------- CloseDocs
// ape_close_list.txt: full paths. Closes each document that is open (without
// saving), so build.py can replace the file with a fresh template copy.
// Verified on AD26: deleting a sheet's objects in place left the old copies.
procedure CloseDocs;
var
    L : TStringList;
    i, n : Integer;
begin
    StartRun('CloseDocs');
    L := TStringList.Create;
    L.LoadFromFile(BRIDGE + 'ape_close_list.txt');
    n := 0;
    for i := 0 to L.Count - 1 do
        if (L[i] <> '') then
            if Client.IsDocumentOpen(L[i]) then
            begin
                ApeLog('closing ' + L[i]);
                Client.CloseDocument(Client.GetDocumentByPath(L[i]));
                n := n + 1;
            end;
    L.Free;
    ApeFinish('{"success": true, "closed": ' + IntToStr(n) + '}');
end;

// -------------------------------------------------------------- NewLib
// ape_new_lib.txt: target path, then kind (SCHLIB or PCBLIB). Opening a missing
// path does not create it and SaveObject/SaveAs raises a dialog, so create a
// new document, name it and save it.
procedure NewLib;
var
    L : TStringList;
    Path, Kind : String;
    Doc : IServerDocument;
begin
    StartRun('NewLib');
    L := TStringList.Create;
    L.LoadFromFile(BRIDGE + 'ape_new_lib.txt');
    Path := Trim(L[0]);
    Kind := 'SCHLIB';
    if (L.Count > 1) then
        if (Trim(L[1]) <> '') then Kind := UpperCase(Trim(L[1]));
    L.Free;
    GetWorkSpace.DM_CreateNewDocument(Kind);
    Doc := Client.CurrentView.OwnerDocument;
    if (UpperCase(Doc.Kind) <> Kind) then
        ApeFinish('{"success": false, "error": "new document is ' + Doc.Kind + ', not ' + Kind + '"}')
    else
    begin
        Doc.SetFileName(Path);
        Doc.Modified := True;
        Doc.DoFileSave('');
        ApeFinish('{"success": true}');
    end;
end;

// ------------------------------------------------- DropDefaultFootprint
// ape_new_lib.txt: PcbLib path. A new PcbLib starts with an empty
// PCBComponent_1; remove it once the library has other footprints, and save.
procedure DropDefaultFootprint;
var
    L : TStringList;
    Path : String;
    Lib : IPCB_Library;
    Comp : IPCB_LibComponent;
    Doc : IServerDocument;
    n : Integer;
begin
    StartRun('DropDefaultFootprint');
    L := TStringList.Create;
    L.LoadFromFile(BRIDGE + 'ape_new_lib.txt');
    Path := Trim(L[0]);
    L.Free;
    Doc := OpenApeDoc('PCBLIB', Path);
    Client.ShowDocument(Doc);
    Lib := PCBServer.GetCurrentPCBLibrary;
    n := 0;
    Comp := Lib.GetComponentByName('PCBComponent_1');
    if (Comp <> nil) and (Lib.ComponentCount > 1) then
    begin
        Lib.RemoveComponent(Comp);
        Lib.Navigate_FirstComponent;
        n := 1;
    end;
    Doc.Modified := True;
    Doc.DoFileSave('');
    ApeFinish('{"success": true, "removed": ' + IntToStr(n) + ', "footprints": ' + IntToStr(Lib.ComponentCount) + '}');
end;

// -------------------------------------------------------- AddToProject
// ape_add_list.txt: project path, then document paths.
procedure AddToProject;
var
    L : TStringList;
    Prj, P : IProject;
    PrjDoc : IServerDocument;
    i, j, added : Integer;
    found : Boolean;
begin
    StartRun('AddToProject');
    L := TStringList.Create;
    L.LoadFromFile(BRIDGE + 'ape_add_list.txt');
    Prj := nil;
    for i := 0 to GetWorkspace.DM_ProjectCount - 1 do
    begin
        P := GetWorkspace.DM_Projects(i);
        if (UpperCase(P.DM_ProjectFullPath) = UpperCase(L[0])) then Prj := P;
    end;
    if (Prj = nil) then
        ApeFinish('{"success": false, "error": "project is not open in Altium"}')
    else
    begin
        added := 0;
        for i := 1 to L.Count - 1 do
            if (L[i] <> '') then
            begin
                found := False;
                for j := 0 to Prj.DM_LogicalDocumentCount - 1 do
                    if (UpperCase(Prj.DM_LogicalDocuments(j).DM_FullPath) = UpperCase(L[i])) then
                        found := True;
                if not found then
                begin
                    ApeLog('adding ' + L[i]);
                    Prj.DM_AddSourceDocument(L[i]);
                    added := added + 1;
                end;
            end;
        // WorkspaceManager:SaveObject with ObjectKind=Project does nothing
        // on AD26; saving the project's server document works.
        ApeLog('saving project');
        PrjDoc := Client.GetDocumentByPath(L[0]);
        PrjDoc.Modified := True;
        PrjDoc.DoFileSave(PrjDoc.Kind);
        ApeFinish('{"success": true, "added": ' + IntToStr(added) + '}');
    end;
    L.Free;
end;

// ----------------------------------------- CloseApeProject / OpenApeProject
// ape_project.txt: the .PrjPcb path, then a document of the project. Close
// saves the project's open documents and closes the project with them, so
// build.py can edit the project file; Open opens the project again.
function FindApeProject(Path : String) : IProject;
var
    i : Integer;
begin
    Result := nil;
    for i := 0 to GetWorkspace.DM_ProjectCount - 1 do
        if (UpperCase(GetWorkspace.DM_Projects(i).DM_ProjectFullPath) = UpperCase(Path)) then
            Result := GetWorkspace.DM_Projects(i);
end;

procedure CloseApeProject;
var
    L : TStringList;
    Prj : IProject;
    Doc : IServerDocument;
    j, n : Integer;
    P : String;
begin
    StartRun('CloseApeProject');
    L := TStringList.Create;
    L.LoadFromFile(BRIDGE + 'ape_project.txt');
    Prj := FindApeProject(Trim(L[0]));
    if (Prj = nil) then
    begin
        ApeFinish('{"success": true, "closed": false}');
        Exit;
    end;
    n := 0;
    for j := 0 to Prj.DM_LogicalDocumentCount - 1 do
    begin
        P := Prj.DM_LogicalDocuments(j).DM_FullPath;
        if Client.IsDocumentOpen(P) then
        begin
            Doc := Client.GetDocumentByPath(P);
            if Doc.Modified then
            begin
                ApeLog('saving ' + P);
                Doc.DoFileSave('');
                n := n + 1;
            end;
        end;
    end;
    // focus the project through one of its documents, then close it all
    Client.ShowDocument(OpenApeDoc('PCB', Trim(L[1])));
    ApeLog('closing project');
    ResetParameters;
    AddStringParameter('ObjectKind', 'FocusedProjectAndDocuments');
    RunProcess('WorkspaceManager:CloseObject');
    L.Free;
    ApeFinish('{"success": true, "closed": true, "saved": ' + IntToStr(n) + '}');
end;

procedure OpenApeProject;
var
    L : TStringList;
begin
    StartRun('OpenApeProject');
    L := TStringList.Create;
    L.LoadFromFile(BRIDGE + 'ape_project.txt');
    ResetParameters;
    AddStringParameter('ObjectKind', 'Project');
    AddStringParameter('FileName', Trim(L[0]));
    RunProcess('WorkspaceManager:OpenObject');
    if (FindApeProject(Trim(L[0])) = nil) then
        ApeFinish('{"success": false, "error": "project did not open"}')
    else
        ApeFinish('{"success": true}');
    L.Free;
end;

// ---------------------------------------------------------- BuildSheet
// Adapted from altium-mcp dev/build_circuit.pas. ape_sheet_spec.txt:
//   SHEET|<full .SchDoc path>       STYLE|<sheet style>
//   PART|desig|symlib|symbol|partid|x|y|orient|mirror
//   COMMENT|t  DESCRIPTION|t  FOOTPRINT|n  PARAM|name|value
//   WIRE|x1|y1|x2|y2[|...]  JUNCTION|x|y  NOERC|x|y
//   NETLABEL|x|y|orient|justification|text
//   POWER|x|y|orient|style|text|shownet   NOTE|x|y|text ('* ' prefix)
// Clears what a previous run generated, builds, saves, and writes the
// electrical end of every placed pin to ape_pin_map.txt.
procedure BuildSheet;
var
    Spec, PinMap : TStringList;
    DelList : TInterfaceList;
    Rec, Kind, SheetPath, CurLib, Missing, PName : String;
    i, k, v, Parts, Gfx, x, y, len : Integer;
    found : Boolean;
    ServerDoc : IServerDocument;
    TargetDoc, LibDoc : ISch_Document;
    Iter, PIter : ISch_Iterator;
    Prim, Comp, Pin, Obj, Impl, Param : IDispatch;
begin
    StartRun('BuildSheet');
    Spec := TStringList.Create;
    Spec.LoadFromFile(BRIDGE + 'ape_sheet_spec.txt');
    SheetPath := PipeField(Spec[0], 1);
    ApeLog('sheet ' + SheetPath);
    ServerDoc := OpenApeDoc('SCH', SheetPath);
    Client.ShowDocument(ServerDoc);
    TargetDoc := SchServer.GetSchDocumentByPath(SheetPath);
    if (TargetDoc = nil) then
    begin
        ApeFinish('{"success": false, "error": "could not open target sheet"}');
        Exit;
    end;
    if (TargetDoc.ObjectID <> 32) then
    begin
        ApeFinish('{"success": false, "error": "target is not a schematic"}');
        Exit;
    end;

    // clear previous output
    DelList := TInterfaceList.Create;
    Iter := TargetDoc.SchIterator_Create;
    Iter.AddFilter_ObjectSet(MkSet(eSchComponent, eWire, eNetLabel, ePowerObject, eJunction, eLabel, eNoERC));
    Prim := Iter.FirstSchObject;
    while (Prim <> nil) do
    begin
        if (Prim.ObjectId = eLabel) then
        begin
            if (Copy(Prim.Text, 1, 2) = '* ') then DelList.Add(Prim);
        end
        else
            DelList.Add(Prim);
        Prim := Iter.NextSchObject;
    end;
    TargetDoc.SchIterator_Destroy(Iter);
    ApeLog('removing ' + IntToStr(DelList.Count));
    for i := 0 to DelList.Count - 1 do
        TargetDoc.RemoveSchObject(DelList.Items[i]);
    DelList.Free;

    SchServer.ProcessControl.PreProcess(TargetDoc, '');
    Comp := nil;
    CurLib := '';
    Missing := '';
    Parts := 0;
    Gfx := 0;
    for i := 1 to Spec.Count - 1 do
    begin
        Rec := Spec[i];
        Kind := PipeField(Rec, 0);
        if (Kind = 'STYLE') then
        begin
            // Setting SheetStyle alone leaves SheetSizeX/Y at the template's A
            // size (verified on AD26), so also give the size as a custom sheet.
            TargetDoc.SheetStyle := StrToInt(PipeField(Rec, 1));
            if (PipeField(Rec, 3) <> '') then
            begin
                TargetDoc.UseCustomSheet := True;
                TargetDoc.CustomX := MilsToCoord(StrToInt(PipeField(Rec, 2)));
                TargetDoc.CustomY := MilsToCoord(StrToInt(PipeField(Rec, 3)));
            end;
        end
        else if (Kind = 'PART') then
        begin
            if (PipeField(Rec, 2) <> CurLib) then
            begin
                CurLib := PipeField(Rec, 2);
                ApeLog('library ' + CurLib);
                Client.ShowDocument(OpenApeDoc('SchLib', CurLib));
                Sleep(500);
            end;
            LibDoc := SchServer.GetSchDocumentByPath(CurLib);
            Comp := nil;
            Iter := LibDoc.SchLibIterator_Create;
            Iter.AddFilter_ObjectSet(MkSet(eSchComponent));
            Prim := Iter.FirstSchObject;
            while (Prim <> nil) do
            begin
                if (Prim.LibReference = PipeField(Rec, 3)) then Comp := Prim;
                Prim := Iter.NextSchObject;
            end;
            LibDoc.SchIterator_Destroy(Iter);
            if (Comp = nil) then
                Missing := Missing + PipeField(Rec, 1) + ':' + PipeField(Rec, 3) + ' '
            else
            begin
                Comp := Comp.Replicate;
                Comp.Designator.Text := PipeField(Rec, 1);
                Comp.DesignItemID := PipeField(Rec, 3);
                if (StrToInt(PipeField(Rec, 4)) > 0) then
                    Comp.CurrentPartID := StrToInt(PipeField(Rec, 4));
                Comp.Orientation := StrToInt(PipeField(Rec, 7));
                RegisterObj(TargetDoc, Comp);
                if (PipeField(Rec, 8) = '1') then Comp.Mirror(Comp.Location);
                Comp.MoveByXY(
                    MilsToCoord(StrToInt(PipeField(Rec, 5)) - CoordToMils(Comp.Location.X)),
                    MilsToCoord(StrToInt(PipeField(Rec, 6)) - CoordToMils(Comp.Location.Y)));
                Parts := Parts + 1;
            end;
        end
        else if (Kind = 'COMMENT') then
        begin
            if (Comp <> nil) then Comp.Comment.Text := PipeField(Rec, 1);
        end
        else if (Kind = 'DESCRIPTION') then
        begin
            if (Comp <> nil) then Comp.ComponentDescription := PipeField(Rec, 1);
        end
        else if (Kind = 'FOOTPRINT') then
        begin
            if (Comp <> nil) then
            begin
                // UseComponentLibrary would look for the footprint in the
                // symbol's own SchLib (ECO: "Footprint Not Found" for every
                // part, verified on AD26); False searches the project's
                // libraries, which include lib/APE-SBC.PcbLib.
                Impl := Comp.AddSchImplementation;
                Impl.ModelName := PipeField(Rec, 1);
                Impl.ModelType := 'PCBLIB';
                Impl.IsCurrent := True;
                Impl.UseComponentLibrary := False;
            end;
        end
        else if (Kind = 'PARAM') then
        begin
            if (Comp <> nil) then
            begin
                PName := PipeField(Rec, 1);
                found := False;
                PIter := Comp.SchIterator_Create;
                PIter.AddFilter_ObjectSet(MkSet(eParameter));
                Param := PIter.FirstSchObject;
                while (Param <> nil) do
                begin
                    if (UpperCase(Param.Name) = UpperCase(PName)) then
                    begin
                        Param.Text := PipeField(Rec, 2);
                        found := True;
                    end;
                    Param := PIter.NextSchObject;
                end;
                Comp.SchIterator_Destroy(PIter);
                if not found then
                begin
                    Param := SchServer.SchObjectFactory(eParameter, eCreate_Default);
                    Param.Name := PName;
                    Param.Text := PipeField(Rec, 2);
                    Param.ParamType := eParameterType_String;
                    Param.ReadOnlyState := eReadOnly_None;
                    Param.IsHidden := True;
                    Comp.AddSchObject(Param);
                    SchServer.RobotManager.SendMessage(Comp.I_ObjectAddress, c_BroadCast,
                        SCHM_PrimitiveRegistration, Param.I_ObjectAddress);
                end;
            end;
        end
        else if (Kind = 'WIRE') then
        begin
            Obj := SchServer.SchObjectFactory(eWire, eCreate_GlobalCopy);
            Obj.Location := Point(MilsToCoord(StrToInt(PipeField(Rec, 1))), MilsToCoord(StrToInt(PipeField(Rec, 2))));
            k := 1;
            v := 0;
            while (PipeField(Rec, k) <> '') do
            begin
                v := v + 1;
                Obj.InsertVertex := v;
                Obj.SetState_Vertex(v, Point(MilsToCoord(StrToInt(PipeField(Rec, k))),
                                             MilsToCoord(StrToInt(PipeField(Rec, k + 1)))));
                k := k + 2;
            end;
            RegisterObj(TargetDoc, Obj);
            Gfx := Gfx + 1;
        end
        else if (Kind = 'JUNCTION') or (Kind = 'NOERC') then
        begin
            if (Kind = 'JUNCTION') then
                Obj := SchServer.SchObjectFactory(eJunction, eCreate_GlobalCopy)
            else
            begin
                // A script-created No-ERC suppresses nothing until told to
                // (verified on AD26: floating-input errors stayed).
                Obj := SchServer.SchObjectFactory(eNoERC, eCreate_GlobalCopy);
                Obj.IsActive := True;
                Obj.SuppressAll := True;
            end;
            Obj.Location := Point(MilsToCoord(StrToInt(PipeField(Rec, 1))), MilsToCoord(StrToInt(PipeField(Rec, 2))));
            RegisterObj(TargetDoc, Obj);
            Gfx := Gfx + 1;
        end
        else if (Kind = 'NETLABEL') then
        begin
            Obj := SchServer.SchObjectFactory(eNetLabel, eCreate_GlobalCopy);
            Obj.Location := Point(MilsToCoord(StrToInt(PipeField(Rec, 1))), MilsToCoord(StrToInt(PipeField(Rec, 2))));
            Obj.Orientation := StrToInt(PipeField(Rec, 3));
            Obj.Justification := StrToInt(PipeField(Rec, 4));
            Obj.Text := PipeField(Rec, 5);
            RegisterObj(TargetDoc, Obj);
            Gfx := Gfx + 1;
        end
        else if (Kind = 'POWER') then
        begin
            Obj := SchServer.SchObjectFactory(ePowerObject, eCreate_GlobalCopy);
            Obj.Location := Point(MilsToCoord(StrToInt(PipeField(Rec, 1))), MilsToCoord(StrToInt(PipeField(Rec, 2))));
            Obj.Orientation := StrToInt(PipeField(Rec, 3));
            Obj.Style := StrToInt(PipeField(Rec, 4));
            Obj.ShowNetName := (PipeField(Rec, 6) = '1');
            Obj.Text := PipeField(Rec, 5);
            RegisterObj(TargetDoc, Obj);
            Gfx := Gfx + 1;
        end
        else if (Kind = 'NOTE') then
        begin
            Obj := SchServer.SchObjectFactory(eLabel, eCreate_GlobalCopy);
            Obj.Location := Point(MilsToCoord(StrToInt(PipeField(Rec, 1))), MilsToCoord(StrToInt(PipeField(Rec, 2))));
            Obj.Text := PipeField(Rec, 3);
            RegisterObj(TargetDoc, Obj);
            Gfx := Gfx + 1;
        end;
        if ((i mod 500) = 0) then ApeLog('record ' + IntToStr(i));
    end;
    ApeLog('parts=' + IntToStr(Parts) + ' graphics=' + IntToStr(Gfx));
    TargetDoc.ResetAllSchParametersPosition;
    SchServer.ProcessControl.PostProcess(TargetDoc, '');
    TargetDoc.GraphicallyInvalidate;

    // pin map: electrical end of every visible pin
    PinMap := TStringList.Create;
    Iter := TargetDoc.SchIterator_Create;
    Iter.AddFilter_ObjectSet(MkSet(eSchComponent));
    Comp := Iter.FirstSchObject;
    while (Comp <> nil) do
    begin
        PIter := Comp.SchIterator_Create;
        PIter.AddFilter_ObjectSet(MkSet(ePin));
        Pin := PIter.FirstSchObject;
        while (Pin <> nil) do
        begin
            if ((Pin.OwnerPartId = 0) or (Pin.OwnerPartId = Comp.CurrentPartID)) then
            begin
                x := CoordToMils(Pin.Location.X);
                y := CoordToMils(Pin.Location.Y);
                len := CoordToMils(Pin.PinLength);
                if (Pin.Orientation = 0) then x := x + len
                else if (Pin.Orientation = 1) then y := y + len
                else if (Pin.Orientation = 2) then x := x - len
                else if (Pin.Orientation = 3) then y := y - len;
                PinMap.Add('PIN|' + Comp.Designator.Text + '|' + IntToStr(Comp.CurrentPartID) + '|' +
                           Pin.Designator + '|' + IntToStr(x) + '|' + IntToStr(y));
            end;
            Pin := PIter.NextSchObject;
        end;
        Comp.SchIterator_Destroy(PIter);
        Comp := Iter.NextSchObject;
    end;
    TargetDoc.SchIterator_Destroy(Iter);
    PinMap.SaveToFile(BRIDGE + 'ape_pin_map.txt');

    ApeLog('saving');
    ServerDoc := OpenApeDoc('SCH', SheetPath);
    ServerDoc.Modified := True;
    ServerDoc.DoFileSave('');
    ApeFinish('{"success": true, "parts": ' + IntToStr(Parts) + ', "graphics": ' + IntToStr(Gfx) +
           ', "pins": ' + IntToStr(PinMap.Count) + ', "missing": "' + Missing + '"}');
    PinMap.Free;
    Spec.Free;
end;

// ================================================================== PCB
// Spec files come from gen/pcbsetup.py via build.py `pcb ...`. The first line
// of each is the full .PcbDoc path; lengths are Altium coords (1 mil = 10000),
// so no decimal separator is parsed here.

// The PCB at Path, opened if needed and brought to the front.
function ApeBoard(Path : String) : IPCB_Board;
begin
    Client.ShowDocument(OpenApeDoc('PCB', Path));
    Result := PCBServer.GetPCBBoardByPath(Path);
end;

function LoadSpec(Name : String) : TStringList;
begin
    Result := TStringList.Create;
    Result.LoadFromFile(BRIDGE + Name);
end;

procedure SaveBoard(Path : String);
var
    Doc : IServerDocument;
begin
    Doc := OpenApeDoc('PCB', Path);
    Doc.Modified := True;
    Doc.DoFileSave('');
end;

// First board object of ObjectId whose Name matches (classes also match MemberKind).
function FindBoardObject(Board : IPCB_Board; ObjectId : Integer; Name : String; MemberKind : Integer) : IDispatch;
var
    It : IPCB_BoardIterator;
    Obj : IDispatch;
begin
    Result := nil;
    It := Board.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(ObjectId));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    Obj := It.FirstPCBObject;
    while (Obj <> nil) and (Result = nil) do
    begin
        if (UpperCase(Obj.Name) = UpperCase(Name)) then
            if (ObjectId <> eClassObject) or (Obj.MemberKind = MemberKind) then Result := Obj;
        Obj := It.NextPCBObject;
    end;
    Board.BoardIterator_Destroy(It);
end;

function CountBoardObjects(Board : IPCB_Board; ObjectId : Integer) : Integer;
var
    It : IPCB_BoardIterator;
    Obj : IDispatch;
begin
    Result := 0;
    It := Board.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(ObjectId));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    Obj := It.FirstPCBObject;
    while (Obj <> nil) do
    begin
        Result := Result + 1;
        Obj := It.NextPCBObject;
    end;
    Board.BoardIterator_Destroy(It);
end;

// ---------------------------------------------------------- PcbOutline
procedure SetOutlineVertex(BO : IPCB_BoardOutline; Index, X, Y : Integer);
var
    Seg : TPolySegment;
begin
    Seg := TPolySegment;
    Seg.Kind := ePolySegmentLine;
    Seg.vx := X;
    Seg.vy := Y;
    BO.Segments[Index] := Seg;
end;

// ape_pcb_outline.txt: OUTLINE|x0|y0|width|height. Rectangular board shape,
// board origin at its lower-left corner.
procedure PcbOutline;
var
    Spec : TStringList;
    Board : IPCB_Board;
    BO : IPCB_BoardOutline;
    x0, y0, w, h : Integer;
    R : TCoordRect;
    Path : String;
begin
    StartRun('PcbOutline');
    Spec := LoadSpec('ape_pcb_outline.txt');
    Path := Trim(Spec[0]);
    Board := ApeBoard(Path);
    x0 := StrToInt(PipeField(Spec[1], 1));
    y0 := StrToInt(PipeField(Spec[1], 2));
    w := StrToInt(PipeField(Spec[1], 3));
    h := StrToInt(PipeField(Spec[1], 4));
    Spec.Free;
    BO := Board.BoardOutline;
    ApeLog('outline');
    PCBServer.PreProcess;
    BO.BeginModify;
    BO.PointCount := 4;
    SetOutlineVertex(BO, 0, x0, y0);
    SetOutlineVertex(BO, 1, x0 + w, y0);
    SetOutlineVertex(BO, 2, x0 + w, y0 + h);
    SetOutlineVertex(BO, 3, x0, y0 + h);
    BO.EndModify;
    BO.Invalidate;
    BO.Rebuild;
    BO.Validate;
    PCBServer.PostProcess;
    Board.XOrigin := x0;
    Board.YOrigin := y0;
    Board.ViewManager_FullUpdate;
    R := BO.BoundingRectangle;
    SaveBoard(Path);
    ApeFinish('{"success": true, "points": ' + IntToStr(BO.PointCount) +
              ', "left": ' + IntToStr(R.Left) + ', "bottom": ' + IntToStr(R.Bottom) +
              ', "right": ' + IntToStr(R.Right) + ', "top": ' + IntToStr(R.Top) + '}');
end;

// ------------------------------------------------------------ PcbStack
// ape_pcb_stack.txt: V9 master-stack parameters, one KEY=value per line,
// handed to MasterLayerStack.Import_FromParameters.
procedure PcbStack;
var
    Spec : TStringList;
    Board : IPCB_Board;
    Stack, Layer : IDispatch;
    S, Names, Path : String;
    i : Integer;
begin
    StartRun('PcbStack');
    Spec := LoadSpec('ape_pcb_stack.txt');
    Path := Trim(Spec[0]);
    Board := ApeBoard(Path);
    S := '';
    for i := 1 to Spec.Count - 1 do
        if (Spec[i] <> '') then S := S + Spec[i] + '|';
    Spec.Free;
    Stack := Board.MasterLayerStack;
    ApeLog('import ' + IntToStr(Length(S)) + ' chars');
    PCBServer.PreProcess;
    Stack.Import_FromParameters(S);
    PCBServer.PostProcess;
    ApeLog('imported');
    Names := '';
    Layer := Stack.First(eLayerClass_Physical);
    while (Layer <> nil) do
    begin
        Names := Names + Layer.Name + ', ';
        Layer := Stack.Next(eLayerClass_Physical, Layer);
    end;
    Board.ViewManager_UpdateLayerTabs;
    Board.ViewManager_FullUpdate;
    SaveBoard(Path);
    ApeFinish('{"success": true, "layers": "' + Names + '"}');
end;

// -------------------------------------------------------- PcbImpedance
// ape_pcb_imp.txt: IMP|name|ohms|diff 0/1|tolerance %, then its layers as
// TRACE|layer|width|gap|ref top|ref bottom|mask on trace|mask between
// (0 = none). Replaces every impedance profile of the board; widths and gaps
// are locked, so Altium reports the impedance it calculates for them.
procedure PcbImpedance;
var
    Spec : TStringList;
    Board : IPCB_Board;
    Stack, Sub, Prof, TI : IDispatch;
    i, k, L : Integer;
    Rec, Kind, Res, Path : String;
begin
    StartRun('PcbImpedance');
    Spec := LoadSpec('ape_pcb_imp.txt');
    Path := Trim(Spec[0]);
    Board := ApeBoard(Path);
    Stack := Board.MasterLayerStack;
    Sub := Stack.Substacks[0];
    for k := Stack.GetImpedanceProfileCount - 1 downto 0 do
        Stack.RemoveImpedanceProfile(Stack.GetImpedanceProfileByIndex(k));
    Prof := nil;
    for i := 1 to Spec.Count - 1 do
    begin
        Rec := Spec[i];
        Kind := PipeField(Rec, 0);
        if (Kind = 'IMP') then
        begin
            ApeLog('profile ' + PipeField(Rec, 1));
            Prof := Stack.CreateImpedanceProfile;
            Prof.Name := PipeField(Rec, 1);
            Prof.Impedance := StrToInt(PipeField(Rec, 2));
            Prof.IsDiffPair := (PipeField(Rec, 3) = '1');
            Prof.ImpedanceTolerance := StrToInt(PipeField(Rec, 4));
            for k := 0 to Prof.GetTraceImpedanceCount - 1 do
            begin
                TI := Prof.GetTraceImpedanceByIndex(k);
                TI.IsEnabled := False;
            end;
        end
        else if (Kind = 'TRACE') and (Prof <> nil) then
        begin
            L := StrToInt(PipeField(Rec, 1));
            ApeLog('  layer ' + IntToStr(L));
            TI := Prof.GetTraceImpedanceForLayer(Sub, L);
            if (TI = nil) then TI := Prof.CreateTraceImpedance(Sub, L);
            TI.IsEnabled := True;
            if (StrToInt(PipeField(Rec, 4)) <> 0) then TI.RefTopLayer := StrToInt(PipeField(Rec, 4));
            if (StrToInt(PipeField(Rec, 5)) <> 0) then TI.RefBottomLayer := StrToInt(PipeField(Rec, 5));
            TI.TraceWidth := StrToInt(PipeField(Rec, 2));
            TI.IsTraceWidthLocked := True;
            if Prof.IsDiffPair then
            begin
                TI.DiffPairGap := StrToInt(PipeField(Rec, 3));
                TI.IsTraceGapLocked := True;
            end;
            if (StrToInt(PipeField(Rec, 6)) > 0) then
            begin
                TI.UseSolderMask := True;
                TI.SolderMaskThicknessOnTopOfTraces := StrToInt(PipeField(Rec, 6));
                TI.SolderMaskThicknessBetweenTraces := StrToInt(PipeField(Rec, 7));
            end;
        end;
    end;
    Spec.Free;
    Res := '';
    for k := 0 to Stack.GetImpedanceProfileCount - 1 do
    begin
        Prof := Stack.GetImpedanceProfileByIndex(k);
        Res := Res + Prof.Name + ':';
        for i := 0 to Prof.GetTraceImpedanceCount - 1 do
        begin
            TI := Prof.GetTraceImpedanceByIndex(i);
            if TI.IsEnabled then
                Res := Res + ' ' + IntToStr(TI.Layer) + '=' + IntToStr(TI.TraceWidth) + '/' +
                       IntToStr(TI.DiffPairGap) + '/' + FloatToStr(TI.CalculatedImpedance);
        end;
        Res := Res + '; ';
    end;
    SaveBoard(Path);
    ApeFinish('{"success": true, "profiles": "' + Res + '"}');
end;

// ----------------------------------------------------------- PcbImport
// ape_pcb_import.txt: the .PcbDoc path. Runs Design >> Import Changes (the
// ECO dialog); build.py presses its buttons, and RunProcess returns when the
// dialog closes.
procedure PcbImport;
var
    Spec : TStringList;
    Board : IPCB_Board;
    Path : String;
begin
    StartRun('PcbImport');
    Spec := LoadSpec('ape_pcb_import.txt');
    Path := Trim(Spec[0]);
    Spec.Free;
    Board := ApeBoard(Path);
    ApeLog('eco');
    ResetParameters;
    AddStringParameter('ObjectKind', 'Project');
    AddStringParameter('Action', 'UpdateMe');
    RunProcess('WorkspaceManager:Compare');
    ApeLog('eco closed');
    Board := PCBServer.GetPCBBoardByPath(Path);
    SaveBoard(Path);
    ApeFinish('{"success": true, "components": ' + IntToStr(CountBoardObjects(Board, eComponentObject)) +
              ', "nets": ' + IntToStr(CountBoardObjects(Board, eNetObject)) + '}');
end;

// ------------------------------------------------------------ PcbClear
// ape_pcb_import.txt: the .PcbDoc path. Deletes every component, so the next
// import brings fresh copies of changed footprints (the ECO compares
// footprint names only). Nets, classes, rules and the stack stay.
procedure PcbClear;
var
    Spec : TStringList;
    Board : IPCB_Board;
    It : IPCB_BoardIterator;
    DelList : TInterfaceList;
    Obj : IDispatch;
    Path : String;
    i : Integer;
begin
    StartRun('PcbClear');
    Spec := LoadSpec('ape_pcb_import.txt');
    Path := Trim(Spec[0]);
    Spec.Free;
    Board := ApeBoard(Path);
    DelList := TInterfaceList.Create;
    It := Board.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eComponentObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    Obj := It.FirstPCBObject;
    while (Obj <> nil) do
    begin
        DelList.Add(Obj);
        Obj := It.NextPCBObject;
    end;
    Board.BoardIterator_Destroy(It);
    ApeLog('deleting ' + IntToStr(DelList.Count) + ' components');
    PCBServer.PreProcess;
    for i := 0 to DelList.Count - 1 do
        Board.RemovePCBObject(DelList.Items[i]);
    PCBServer.PostProcess;
    Board.ViewManager_FullUpdate;
    SaveBoard(Path);
    ApeFinish('{"success": true, "deleted": ' + IntToStr(DelList.Count) + ', "left": ' +
              IntToStr(CountBoardObjects(Board, eComponentObject)) + '}');
    DelList.Free;
end;

// ---------------------------------------------------------- PcbClasses
// ape_pcb_classes.txt: NETCLASS|name|net..., DIFFPAIR|name|positive|negative,
// DPCLASS|name|pair... Classes and pairs that exist are refilled.
procedure PcbClasses;
var
    Spec : TStringList;
    Board : IPCB_Board;
    C, DP, P, N : IDispatch;
    i, k, MK, nc, np : Integer;
    Rec, Kind, Missing, Path : String;
begin
    StartRun('PcbClasses');
    Spec := LoadSpec('ape_pcb_classes.txt');
    Path := Trim(Spec[0]);
    Board := ApeBoard(Path);
    Missing := '';
    nc := 0;
    np := 0;
    PCBServer.PreProcess;
    for i := 1 to Spec.Count - 1 do
    begin
        Rec := Spec[i];
        Kind := PipeField(Rec, 0);
        if (Kind = 'NETCLASS') or (Kind = 'DPCLASS') then
        begin
            if (Kind = 'NETCLASS') then MK := eClassMemberKind_Net
            else MK := eClassMemberKind_DifferentialPair;
            ApeLog('class ' + PipeField(Rec, 1));
            C := FindBoardObject(Board, eClassObject, PipeField(Rec, 1), MK);
            if (C = nil) then
            begin
                C := PCBServer.PCBClassFactoryByClassMember(MK);
                C.SuperClass := False;
                C.Name := PipeField(Rec, 1);
                Board.AddPCBObject(C);
            end
            else
                C.RemoveAllMembers;
            k := 2;
            while (PipeField(Rec, k) <> '') do
            begin
                C.AddMemberByName(PipeField(Rec, k));
                k := k + 1;
            end;
            nc := nc + 1;
        end
        else if (Kind = 'DIFFPAIR') then
        begin
            P := FindBoardObject(Board, eNetObject, PipeField(Rec, 2), 0);
            N := FindBoardObject(Board, eNetObject, PipeField(Rec, 3), 0);
            if (P = nil) or (N = nil) then
                Missing := Missing + PipeField(Rec, 1) + ' '
            else
            begin
                DP := FindBoardObject(Board, eDifferentialPairObject, PipeField(Rec, 1), 0);
                if (DP = nil) then
                begin
                    ApeLog('pair ' + PipeField(Rec, 1));
                    DP := PCBServer.PCBObjectFactory(eDifferentialPairObject, eNoDimension, eCreate_Default);
                    DP.Name := PipeField(Rec, 1);
                    DP.PositiveNet := P;
                    DP.NegativeNet := N;
                    Board.AddPCBObject(DP);
                    PCBServer.SendMessageToRobots(Board.I_ObjectAddress, c_Broadcast,
                        PCBM_BoardRegisteration, DP.I_ObjectAddress);
                end
                else
                begin
                    DP.PositiveNet := P;
                    DP.NegativeNet := N;
                end;
                np := np + 1;
            end;
        end;
    end;
    PCBServer.PostProcess;
    Spec.Free;
    SaveBoard(Path);
    ApeFinish('{"success": true, "classes": ' + IntToStr(nc) + ', "pairs": ' + IntToStr(np) +
              ', "missing": "' + Missing + '"}');
end;

// ------------------------------------------------------------ PcbRules
function RuleKindOf(Kind : String) : Integer;
begin
    Result := -1;
    if (Kind = 'CLEARANCE') then Result := eRule_Clearance
    else if (Kind = 'WIDTH') then Result := eRule_MaxMinWidth
    else if (Kind = 'DIFFPAIR') then Result := eRule_DifferentialPairsRouting
    else if (Kind = 'VIA') then Result := eRule_RoutingViaStyle
    else if (Kind = 'HOLESIZE') then Result := eRule_MaxMinHoleSize
    else if (Kind = 'ANNULAR') then Result := eRule_MinimumAnnularRing
    else if (Kind = 'HOLE2HOLE') then Result := eRule_HoleToHoleClearance
    else if (Kind = 'MASK') then Result := eRule_SolderMaskExpansion
    else if (Kind = 'PASTE') then Result := eRule_PasteMaskExpansion
    else if (Kind = 'SLIVER') then Result := eRule_MinimumSolderMaskSliver
    else if (Kind = 'SILKMASK') then Result := eRule_SilkToSolderMaskClearance
    else if (Kind = 'OUTLINE') then Result := eRule_BoardOutlineClearance;
end;

function ProfileIdOf(Board : IPCB_Board; Name : String) : String;
var
    k : Integer;
    Prof : IDispatch;
begin
    Result := '';
    for k := 0 to Board.MasterLayerStack.GetImpedanceProfileCount - 1 do
    begin
        Prof := Board.MasterLayerStack.GetImpedanceProfileByIndex(k);
        if (UpperCase(Prof.Name) = UpperCase(Name)) then Result := Prof.Id;
    end;
end;

// Field Index of a 'a:b:c' item.
function ColonField(S : String; Index : Integer) : String;
begin
    Result := PipeField(StringReplace(S, ':', '|', MkSet(rfReplaceAll)), Index);
end;

// ape_pcb_rules.txt: ROOM|name|scope|x1|y1|x2|y2, then
// RULE|kind|name|scope1|scope2|values... (see gen/pcbsetup.py rules()).
// Every existing rule of a kind named in the file is deleted first. Altium
// gives each new rule priority 1 (verified on AD26), so the records are added
// last to first and their order in the file is the priority order per kind.
procedure PcbRules;
var
    Spec, Kinds, Rooms, Lay : TStringList;
    DelList : TInterfaceList;
    Board : IPCB_Board;
    It : IPCB_BoardIterator;
    Rule : IDispatch;
    i, k, RK, L : Integer;
    Rec, Kind, SubId, Prof, Path, Bad : String;
begin
    StartRun('PcbRules');
    Spec := LoadSpec('ape_pcb_rules.txt');
    Path := Trim(Spec[0]);
    Board := ApeBoard(Path);
    SubId := Board.MasterLayerStack.Substacks[0].Id;
    Kinds := TStringList.Create;
    Rooms := TStringList.Create;
    Bad := '';
    for i := 1 to Spec.Count - 1 do
        if (PipeField(Spec[i], 0) = 'RULE') then
        begin
            RK := RuleKindOf(PipeField(Spec[i], 1));
            if (RK < 0) then Bad := Bad + PipeField(Spec[i], 1) + ' '
            else Kinds.Add(IntToStr(RK));
        end
        else if (PipeField(Spec[i], 0) = 'ROOM') then
            Rooms.Add(UpperCase(PipeField(Spec[i], 1)));
    if (Bad <> '') then
    begin
        ApeFinish('{"success": false, "error": "unknown rule kinds: ' + Bad + '"}');
        Exit;
    end;

    DelList := TInterfaceList.Create;
    It := Board.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eRuleObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    Rule := It.FirstPCBObject;
    while (Rule <> nil) do
    begin
        if (Kinds.IndexOf(IntToStr(Rule.RuleKind)) >= 0) then DelList.Add(Rule)
        else if (Rule.RuleKind = eRule_ConfinementConstraint) and (Rooms.IndexOf(UpperCase(Rule.Name)) >= 0) then
            DelList.Add(Rule);
        Rule := It.NextPCBObject;
    end;
    Board.BoardIterator_Destroy(It);
    ApeLog('deleting ' + IntToStr(DelList.Count) + ' rules');
    PCBServer.PreProcess;
    for i := 0 to DelList.Count - 1 do
        Board.RemovePCBObject(DelList.Items[i]);
    DelList.Free;

    for i := Spec.Count - 1 downto 1 do
    begin
        Rec := Spec[i];
        Kind := PipeField(Rec, 0);
        if (Kind = 'ROOM') then
        begin
            ApeLog('room ' + PipeField(Rec, 1));
            Rule := PCBServer.PCBRuleFactory(eRule_ConfinementConstraint);
            Rule.Name := PipeField(Rec, 1);
            Rule.Scope1Expression := PipeField(Rec, 2);
            Rule.Kind := eConfineIn;
            Rule.ConstraintLayer := eTopLayer;
            Rule.BoundingRect := RectToCoordRect(Rect(StrToInt(PipeField(Rec, 3)), StrToInt(PipeField(Rec, 6)),
                                                      StrToInt(PipeField(Rec, 5)), StrToInt(PipeField(Rec, 4))));
            Rule.Comment := 'SiP fan-out region (gen/pcbsetup.py); move it with U1';
            Board.AddPCBObject(Rule);
        end
        else if (Kind = 'RULE') then
        begin
            Kind := PipeField(Rec, 1);
            ApeLog('rule ' + PipeField(Rec, 2));
            Rule := PCBServer.PCBRuleFactory(RuleKindOf(Kind));
            Rule.Name := PipeField(Rec, 2);
            Rule.Scope1Expression := PipeField(Rec, 3);
            if (PipeField(Rec, 4) <> '') then Rule.Scope2Expression := PipeField(Rec, 4);
            Rule.Comment := 'APE-SBC setup (gen/pcbsetup.py)';
            if (Kind = 'CLEARANCE') or (Kind = 'HOLE2HOLE') then
                Rule.Gap := StrToInt(PipeField(Rec, 5))
            else if (Kind = 'OUTLINE') then
            begin
                // set the clearance matrix too: every object kind (arc .. hole)
                // against the outline edge. The rule's Descriptor keeps saying
                // Gap=0mil on AD26; GetClearance returns the value set here.
                Rule.Gap := StrToInt(PipeField(Rec, 5));
                for k := eObjectClearanceID_Arc to eObjectClearanceID_Hole do
                begin
                    Rule.SetClearance(k, eObjectClearanceID_OutlineEdge, StrToInt(PipeField(Rec, 5)));
                    Rule.SetClearance(eObjectClearanceID_OutlineEdge, k, StrToInt(PipeField(Rec, 5)));
                end;
            end
            else if (Kind = 'WIDTH') then
            begin
                // min|preferred|max|profile|layer:preferred;...
                Rule.MinLimit := StrToInt(PipeField(Rec, 5));
                Rule.MaxLimit := StrToInt(PipeField(Rec, 7));
                Rule.PreferedWidth := StrToInt(PipeField(Rec, 6));
                Lay := TStringList.Create;
                Lay.Delimiter := ';';
                Lay.StrictDelimiter := True;
                Lay.DelimitedText := PipeField(Rec, 9);
                for k := 0 to Lay.Count - 1 do
                    if (Lay[k] <> '') then
                    begin
                        L := StrToInt(ColonField(Lay[k], 0));
                        Rule.SetState_FavoredWidthAtSubStack(L, SubId, StrToInt(ColonField(Lay[k], 1)));
                    end;
                Lay.Free;
                Prof := PipeField(Rec, 8);
                if (Prof <> '') then
                begin
                    Rule.ImpedanceProfileId := ProfileIdOf(Board, Prof);
                    Rule.ImpedanceDriven := True;
                end;
            end
            else if (Kind = 'DIFFPAIR') then
            begin
                // min w|max w|min gap|max gap|max uncoupled|profile|layer:w:gap;...
                Rule.MaxUncoupledLength := StrToInt(PipeField(Rec, 9));
                Lay := TStringList.Create;
                Lay.Delimiter := ';';
                Lay.StrictDelimiter := True;
                Lay.DelimitedText := PipeField(Rec, 11);
                for k := 0 to Lay.Count - 1 do
                    if (Lay[k] <> '') then
                    begin
                        L := StrToInt(ColonField(Lay[k], 0));
                        Rule.SetState_MinWidthAtSubStack(L, SubId, StrToInt(PipeField(Rec, 5)));
                        Rule.SetState_MaxWidthAtSubStack(L, SubId, StrToInt(PipeField(Rec, 6)));
                        Rule.SetState_PreferedWidthAtSubStack(L, SubId, StrToInt(ColonField(Lay[k], 1)));
                        Rule.SetState_MinGapAtSubStack(L, SubId, StrToInt(PipeField(Rec, 7)));
                        Rule.SetState_MaxGapAtSubStack(L, SubId, StrToInt(PipeField(Rec, 8)));
                        Rule.SetState_PreferedGapAtSubStack(L, SubId, StrToInt(ColonField(Lay[k], 2)));
                    end;
                Lay.Free;
                Prof := PipeField(Rec, 10);
                if (Prof <> '') then
                begin
                    Rule.ImpedanceProfileId := ProfileIdOf(Board, Prof);
                    Rule.ImpedanceDriven := True;
                end;
            end
            else if (Kind = 'VIA') then
            begin
                Rule.MinHoleWidth := StrToInt(PipeField(Rec, 5));
                Rule.PreferedHoleWidth := StrToInt(PipeField(Rec, 6));
                Rule.MaxHoleWidth := StrToInt(PipeField(Rec, 7));
                Rule.MinWidth := StrToInt(PipeField(Rec, 8));
                Rule.PreferedWidth := StrToInt(PipeField(Rec, 9));
                Rule.MaxWidth := StrToInt(PipeField(Rec, 10));
            end
            else if (Kind = 'HOLESIZE') then
            begin
                Rule.AbsoluteValues := True;
                Rule.MinLimit := StrToInt(PipeField(Rec, 5));
                Rule.MaxLimit := StrToInt(PipeField(Rec, 6));
            end
            else if (Kind = 'ANNULAR') then
                Rule.Minimum := StrToInt(PipeField(Rec, 5))
            else if (Kind = 'MASK') or (Kind = 'PASTE') then
                Rule.Expansion := StrToInt(PipeField(Rec, 5))
            else if (Kind = 'SLIVER') then
                Rule.MinSolderMaskSliver := StrToInt(PipeField(Rec, 5))
            else if (Kind = 'SILKMASK') then
                Rule.SilkToMaskGap := StrToInt(PipeField(Rec, 5));
            Board.AddPCBObject(Rule);
        end;
    end;
    PCBServer.PostProcess;
    Kinds.Free;
    Rooms.Free;
    Spec.Free;
    SaveBoard(Path);
    ApeFinish('{"success": true}');
end;

// ----------------------------------------------------------- PcbReport
// ape_pcb_report.txt: outline, stack, impedance profiles, classes,
// differential pairs and rules (kind, priority, scopes, descriptor), counts.
procedure PcbReport;
var
    Spec, Rep : TStringList;
    Board : IPCB_Board;
    It : IPCB_BoardIterator;
    GI : IPCB_GroupIterator;
    Obj, Stack, Layer, Prof, TI, Pad : IDispatch;
    i, k : Integer;
    S : String;
    R : TCoordRect;
begin
    StartRun('PcbReport');
    Spec := LoadSpec('ape_pcb_report_in.txt');
    Board := ApeBoard(Trim(Spec[0]));
    Spec.Free;
    Rep := TStringList.Create;
    R := Board.BoardOutline.BoundingRectangle;
    Rep.Add('OUTLINE|' + IntToStr(Board.BoardOutline.PointCount) + '|' + IntToStr(R.Left) + '|' +
            IntToStr(R.Bottom) + '|' + IntToStr(R.Right) + '|' + IntToStr(R.Top) + '|' +
            IntToStr(Board.XOrigin) + '|' + IntToStr(Board.YOrigin));
    Stack := Board.MasterLayerStack;
    Layer := Stack.First(eLayerClass_Physical);
    while (Layer <> nil) do
    begin
        Rep.Add('LAYER|' + Layer.Name);
        Layer := Stack.Next(eLayerClass_Physical, Layer);
    end;
    for k := 0 to Stack.GetImpedanceProfileCount - 1 do
    begin
        Prof := Stack.GetImpedanceProfileByIndex(k);
        S := 'PROFILE|' + Prof.Name + '|' + Prof.Id;
        for i := 0 to Prof.GetTraceImpedanceCount - 1 do
        begin
            TI := Prof.GetTraceImpedanceByIndex(i);
            if TI.IsEnabled then
                S := S + '|' + IntToStr(TI.Layer) + '=' + IntToStr(TI.TraceWidth) + '/' +
                     IntToStr(TI.DiffPairGap) + '/' + FloatToStr(TI.CalculatedImpedance);
        end;
        Rep.Add(S);
    end;
    It := Board.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eClassObject, eDifferentialPairObject, eRuleObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    Obj := It.FirstPCBObject;
    while (Obj <> nil) do
    begin
        if (Obj.ObjectId = eClassObject) then
        begin
            S := 'CLASS|' + IntToStr(Obj.MemberKind) + '|' + Obj.Name + '|';
            k := 0;
            while (Obj.MemberName[k] <> '') do
            begin
                S := S + Obj.MemberName[k] + ' ';
                k := k + 1;
            end;
            Rep.Add(S);
        end
        else if (Obj.ObjectId = eDifferentialPairObject) then
        begin
            S := 'PAIR|' + Obj.Name + '|';
            if (Obj.PositiveNet <> nil) then S := S + Obj.PositiveNet.Name;
            S := S + '|';
            if (Obj.NegativeNet <> nil) then S := S + Obj.NegativeNet.Name;
            Rep.Add(S);
        end
        else
            Rep.Add('RULE|' + IntToStr(Obj.RuleKind) + '|' + IntToStr(Obj.Priority) + '|' + Obj.Name + '|' +
                    Obj.Scope1Expression + '|' + Obj.Scope2Expression + '|' + Obj.Descriptor);
        Obj := It.NextPCBObject;
    end;
    Board.BoardIterator_Destroy(It);
    // every component's footprint and every pad's net, for build.py's check
    It := Board.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eComponentObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    Obj := It.FirstPCBObject;
    while (Obj <> nil) do
    begin
        Rep.Add('COMP|' + Obj.Name.Text + '|' + Obj.Pattern);
        GI := Obj.GroupIterator_Create;
        GI.AddFilter_ObjectSet(MkSet(ePadObject));
        Pad := GI.FirstPCBObject;
        while (Pad <> nil) do
        begin
            S := '';
            if (Pad.Net <> nil) then S := Pad.Net.Name;
            Rep.Add('PAD|' + Obj.Name.Text + '|' + Pad.Name + '|' + S);
            Pad := GI.NextPCBObject;
        end;
        Obj.GroupIterator_Destroy(GI);
        Obj := It.NextPCBObject;
    end;
    Board.BoardIterator_Destroy(It);
    Rep.Add('COUNT|components|' + IntToStr(CountBoardObjects(Board, eComponentObject)));
    Rep.Add('COUNT|nets|' + IntToStr(CountBoardObjects(Board, eNetObject)));
    Rep.SaveToFile(BRIDGE + 'ape_pcb_report.txt');
    ApeFinish('{"success": true, "lines": ' + IntToStr(Rep.Count) + '}');
    Rep.Free;
end;

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
    ApeFinish('{"success": true, "version": 4}');
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
                Impl := Comp.AddSchImplementation;
                Impl.ModelName := PipeField(Rec, 1);
                Impl.ModelType := 'PCBLIB';
                Impl.IsCurrent := True;
                Impl.UseComponentLibrary := True;
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

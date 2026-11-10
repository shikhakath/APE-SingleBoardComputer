// ApePlace - board outline with rounded corners and assembly notes for placement.
//
// Run from hardware/gen/placement.py, which launches
//   X2.EXE -RScriptingSystem:RunScript(ProjectName="...\ApePlace.PrjScr"|ProcName="ApePlace>PlaceBoard")
// A script project of its own so that it cannot disturb ApeScripts (see
// README section 8 for why the MCP sandbox is not used for this).
//
// ape_place_board.txt, lengths in Altium coords (1 mil = 10000):
//   <full path of the .PcbDoc>
//   OUTLINE|x0|y0|width|height|radius
//   NOTE_TRACK|x1|y1|x2|y2|width       free track on Mechanical 13
//   NOTE_TEXT|x|y|height|strokewidth|text
// Earlier notes (free tracks and texts on Mechanical 13) are removed first.

const
    BRIDGE = 'C:\Users\Public\altium_mcp\';

var
    LogLines : TStringList;

procedure PlaceLog(Msg : String);
begin
    LogLines.Add(Msg);
    LogLines.SaveToFile(BRIDGE + 'ape_log.txt');
end;

procedure PlaceFinish(Json : String);
var
    R : TStringList;
begin
    PlaceLog('finish');
    R := TStringList.Create;
    R.Add(Json);
    R.SaveToFile(BRIDGE + 'ape_result.json');
    R.Free;
end;

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

function OpenDoc(Path : String) : IServerDocument;
begin
    if Client.IsDocumentOpen(Path) then
        Result := Client.GetDocumentByPath(Path)
    else
        Result := Client.OpenDocument('PCB', Path);
end;

procedure SetLine(BO : IPCB_BoardOutline; Index, X, Y : Integer);
var
    Seg : TPolySegment;
begin
    Seg := TPolySegment;
    Seg.Kind := ePolySegmentLine;
    Seg.vx := X;
    Seg.vy := Y;
    BO.Segments[Index] := Seg;
end;

procedure SetArc(BO : IPCB_BoardOutline; Index, X, Y, CX, CY, Rad : Integer; A1, A2 : Double);
var
    Seg : TPolySegment;
begin
    Seg := TPolySegment;
    Seg.Kind := ePolySegmentArc;
    Seg.vx := X;
    Seg.vy := Y;
    Seg.cx := CX;
    Seg.cy := CY;
    Seg.Radius := Rad;
    Seg.Angle1 := A1;
    Seg.Angle2 := A2;
    BO.Segments[Index] := Seg;
end;

procedure PlaceBoard;
var
    Spec : TStringList;
    Path, Rec, Kind : String;
    Board : IPCB_Board;
    Doc : IServerDocument;
    BO : IPCB_BoardOutline;
    It : IPCB_BoardIterator;
    Obj : IPCB_Primitive;
    Dead : TInterfaceList;
    Trk : IPCB_Track;
    Txt : IPCB_Text;
    NoteLayer : TLayer;
    i, x0, y0, w, h, r, Notes : Integer;
    Box : TCoordRect;
begin
    LogLines := TStringList.Create;
    PlaceLog('PlaceBoard start');
    Spec := TStringList.Create;
    Spec.LoadFromFile(BRIDGE + 'ape_place_board.txt');
    Path := Trim(Spec[0]);
    Doc := OpenDoc(Path);
    Client.ShowDocument(Doc);
    Board := PCBServer.GetPCBBoardByPath(Path);
    NoteLayer := String2Layer('Mechanical Layer 13');

    PlaceLog('removing old notes');
    Dead := TInterfaceList.Create;
    It := Board.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eTrackObject, eTextObject));
    It.AddFilter_LayerSet(MkSet(NoteLayer));
    It.AddFilter_Method(eProcessFree);
    Obj := It.FirstPCBObject;
    while (Obj <> nil) do
    begin
        Dead.Add(Obj);
        Obj := It.NextPCBObject;
    end;
    Board.BoardIterator_Destroy(It);

    PCBServer.PreProcess;
    for i := 0 to Dead.Count - 1 do
        Board.RemovePCBObject(Dead.Items[i]);
    Dead.Free;

    Notes := 0;
    for i := 1 to Spec.Count - 1 do
    begin
        Rec := Spec[i];
        Kind := Field(Rec, 0);
        if (Kind = 'OUTLINE') then
        begin
            PlaceLog('outline');
            x0 := StrToInt(Field(Rec, 1));
            y0 := StrToInt(Field(Rec, 2));
            w := StrToInt(Field(Rec, 3));
            h := StrToInt(Field(Rec, 4));
            r := StrToInt(Field(Rec, 5));
            BO := Board.BoardOutline;
            BO.BeginModify;
            BO.PointCount := 8;
            SetLine(BO, 0, x0 + r, y0);
            SetArc(BO, 1, x0 + w - r, y0, x0 + w - r, y0 + r, r, 270.0, 360.0);
            SetLine(BO, 2, x0 + w, y0 + r);
            SetArc(BO, 3, x0 + w, y0 + h - r, x0 + w - r, y0 + h - r, r, 0.0, 90.0);
            SetLine(BO, 4, x0 + w - r, y0 + h);
            SetArc(BO, 5, x0 + r, y0 + h, x0 + r, y0 + h - r, r, 90.0, 180.0);
            SetLine(BO, 6, x0, y0 + h - r);
            SetArc(BO, 7, x0, y0 + r, x0 + r, y0 + r, r, 180.0, 270.0);
            BO.EndModify;
            BO.Invalidate;
            BO.Rebuild;
            BO.Validate;
            Board.XOrigin := x0;
            Board.YOrigin := y0;
        end
        else if (Kind = 'NOTE_TRACK') then
        begin
            Trk := PCBServer.PCBObjectFactory(eTrackObject, eNoDimension, eCreate_Default);
            Trk.x1 := StrToInt(Field(Rec, 1));
            Trk.y1 := StrToInt(Field(Rec, 2));
            Trk.x2 := StrToInt(Field(Rec, 3));
            Trk.y2 := StrToInt(Field(Rec, 4));
            Trk.Width := StrToInt(Field(Rec, 5));
            Trk.Layer := NoteLayer;
            Board.AddPCBObject(Trk);
            Notes := Notes + 1;
        end
        else if (Kind = 'NOTE_TEXT') then
        begin
            Txt := PCBServer.PCBObjectFactory(eTextObject, eNoDimension, eCreate_Default);
            Txt.XLocation := StrToInt(Field(Rec, 1));
            Txt.YLocation := StrToInt(Field(Rec, 2));
            Txt.Size := StrToInt(Field(Rec, 3));
            Txt.Width := StrToInt(Field(Rec, 4));
            Txt.Text := Field(Rec, 5);
            Txt.Layer := NoteLayer;
            Board.AddPCBObject(Txt);
            Notes := Notes + 1;
        end;
    end;
    PCBServer.PostProcess;
    Board.ViewManager_FullUpdate;

    Box := Board.BoardOutline.BoundingRectangle;
    Doc.Modified := True;
    Doc.DoFileSave('');
    PlaceFinish('{"success": true, "points": ' + IntToStr(Board.BoardOutline.PointCount) +
                ', "notes": ' + IntToStr(Notes) +
                ', "left": ' + IntToStr(Box.Left) + ', "bottom": ' + IntToStr(Box.Bottom) +
                ', "right": ' + IntToStr(Box.Right) + ', "top": ' + IntToStr(Box.Top) + '}');
    Spec.Free;
end;

// Reference designators are hidden on every part, top and bottom. New parts from Update PCB
// arrive with theirs visible, so every refresh hides them again.
function HideDesignators(Board : IPCB_Board) : Integer;
var
    It : IPCB_BoardIterator;
    Comp : IPCB_Component;
begin
    Result := 0;
    It := Board.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eComponentObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    Comp := It.FirstPCBObject;
    while (Comp <> nil) do
    begin
        if (Comp.NameOn) then
        begin
            Comp.NameOn := False;
            Result := Result + 1;
        end;
        Comp := It.NextPCBObject;
    end;
    Board.BoardIterator_Destroy(It);
end;

// Rebuilds the connection lines after parts were moved by script (the file keeps them in
// Connections6, so without this the ratsnest still points at the old positions), hides the
// designators, then saves. Same calls as the MCP's layout duplicator. Input: first line of
// ape_place_board.txt.
procedure PlaceRefresh;
var
    Spec : TStringList;
    Path : String;
    Board : IPCB_Board;
    Doc : IServerDocument;
begin
    LogLines := TStringList.Create;
    PlaceLog('PlaceRefresh start');
    Spec := TStringList.Create;
    Spec.LoadFromFile(BRIDGE + 'ape_place_board.txt');
    Path := Trim(Spec[0]);
    Spec.Free;
    Doc := OpenDoc(Path);
    Client.ShowDocument(Doc);
    Board := PCBServer.GetPCBBoardByPath(Path);
    PlaceLog('update connectivity');
    ResetParameters;
    RunProcess('PCB:UpdateConnectivity');
    PlaceLog('validate nets');
    Board.ConnectivelyValidateNets;
    PlaceLog('hid designators: ' + IntToStr(HideDesignators(Board)));
    Board.ViewManager_FullUpdate;
    PlaceLog('saving');
    Doc.Modified := True;
    Doc.DoFileSave('');
    PlaceFinish('{"success": true}');
end;

// ------------------------------------------------------------- RemoveListed
// Removes free tracks and vias named in ape_remove_list.txt by exact coordinates from the board origin. The first line is the
// board's path; then TRK|layer|x1|y1|x2|y2 or VIA|x|y.
procedure RemoveListed;
var
    Spec, Keys : TStringList;
    Path, Key : String;
    Board : IPCB_Board;
    Doc : IServerDocument;
    It : IPCB_BoardIterator;
    Obj : IDispatch;
    DelList : TInterfaceList;
    i, X0, Y0, Listed, Removed : Integer;
begin
    LogLines := TStringList.Create;
    PlaceLog('RemoveListed start');
    Spec := TStringList.Create;
    Spec.LoadFromFile(BRIDGE + 'ape_remove_list.txt');
    Path := Trim(Spec[0]);
    Doc := OpenDoc(Path);
    Client.ShowDocument(Doc);
    Board := PCBServer.GetPCBBoardByPath(Path);
    X0 := Board.XOrigin;
    Y0 := Board.YOrigin;
    Keys := TStringList.Create;
    Keys.Sorted := True;
    for i := 1 to Spec.Count - 1 do
        Keys.Add(Trim(Spec[i]));
    Listed := Keys.Count;
    DelList := TInterfaceList.Create;
    It := Board.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eViaObject, eTrackObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    Obj := It.FirstPCBObject;
    while (Obj <> nil) do
    begin
        if (not Obj.InComponent) and (not Obj.InPolygon) then
        begin
            if (Obj.ObjectId = eViaObject) then
                Key := 'VIA|' + IntToStr(Obj.x - X0) + '|' + IntToStr(Obj.y - Y0)
            else
                Key := 'TRK|' + IntToStr(Obj.Layer) + '|' + IntToStr(Obj.x1 - X0) + '|' + IntToStr(Obj.y1 - Y0) +
                       '|' + IntToStr(Obj.x2 - X0) + '|' + IntToStr(Obj.y2 - Y0);
            if (Keys.IndexOf(Key) >= 0) then DelList.Add(Obj);
        end;
        Obj := It.NextPCBObject;
    end;
    Board.BoardIterator_Destroy(It);
    Removed := DelList.Count;
    PlaceLog('removing ' + IntToStr(Removed) + ' of ' + IntToStr(Listed));
    PCBServer.PreProcess;
    for i := 0 to DelList.Count - 1 do
        Board.RemovePCBObject(DelList.Items[i]);
    PCBServer.PostProcess;
    Board.ViewManager_FullUpdate;
    Doc.DoFileSave('');
    PlaceFinish('{"success": true, "listed": ' + IntToStr(Listed) + ', "removed": ' + IntToStr(Removed) + '}');
end;

// ------------------------------------------------------------- PlacePower
// Power and GND copper, computed by gen/powerplanes.py. ape_place_power.txt, lengths in Altium coords
// relative to the board origin:
//   <full path of the .PcbDoc>
//   NET|name                      a net this file owns: its free vias, tracks and polygons are replaced
//   SIGNET|name                   a signal net with fan-out copper: free vias and tracks are replaced only inside AREA
//   AREA|x1|y1|x2|y2              so copper elsewhere on those nets stays
//   VIA|x|y|hole|diameter|net
//   TRK|layer|x1|y1|x2|y2|width|net
//   POLY|layer|net|order|x,y;x,y;...      poured in file order, small first, so larger ones pour around
// Layers are old layer numbers (1 to 7, 32). Other nets' copper is left alone. Also used for gen/fanout.py.
function NetByName(Board : IPCB_Board; Name : String) : IDispatch;
var
    It : IPCB_BoardIterator;
    Net : IDispatch;
begin
    Result := nil;
    It := Board.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eNetObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    Net := It.FirstPCBObject;
    while (Net <> nil) do
    begin
        if (Net.Name = Name) then
        begin
            Result := Net;
            break;
        end;
        Net := It.NextPCBObject;
    end;
    Board.BoardIterator_Destroy(It);
end;

// ------------------------------------------------------------- MergeNets
// ape_merge.txt: the board's path, then old|new per line. Every pad, track, arc, via, fill, region and polygon on net
// old moves to net new (which must exist), then net old is removed. Used before an ECO that merges nets, so routed
// copper keeps a net instead of going to No Net. Nothing moves, nothing is repoured and nothing is saved.
procedure MergeNets;
var
    Spec : TStringList;
    Path, OldName, NewName : String;
    Board : IPCB_Board;
    Doc : IServerDocument;
    It : IPCB_BoardIterator;
    Obj, NewNet, OldNet : IDispatch;
    Moved, Gone : TInterfaceList;
    i, k, Total, Missing : Integer;
begin
    LogLines := TStringList.Create;
    PlaceLog('MergeNets start');
    Spec := TStringList.Create;
    Spec.LoadFromFile(BRIDGE + 'ape_merge.txt');
    Path := Trim(Spec[0]);
    Doc := OpenDoc(Path);
    Client.ShowDocument(Doc);
    Board := PCBServer.GetPCBBoardByPath(Path);
    Total := 0;
    Missing := 0;
    Gone := TInterfaceList.Create;
    for k := 1 to Spec.Count - 1 do
    begin
        OldName := Field(Trim(Spec[k]), 0);
        NewName := Field(Trim(Spec[k]), 1);
        NewNet := nil;
        if (OldName <> '') and (NewName <> '') then NewNet := NetByName(Board, NewName);
        if (NewNet = nil) then
        begin
            if (OldName <> '') then Missing := Missing + 1;
        end
        else
        begin
            Moved := TInterfaceList.Create;
            It := Board.BoardIterator_Create;
            It.AddFilter_ObjectSet(MkSet(ePadObject, eTrackObject, eArcObject, eViaObject, eFillObject, eRegionObject, ePolyObject));
            It.AddFilter_LayerSet(AllLayers);
            It.AddFilter_Method(eProcessAll);
            Obj := It.FirstPCBObject;
            while (Obj <> nil) do
            begin
                if (Obj.Net <> nil) then
                    if (Obj.Net.Name = OldName) then Moved.Add(Obj);
                Obj := It.NextPCBObject;
            end;
            Board.BoardIterator_Destroy(It);
            PCBServer.PreProcess;
            for i := 0 to Moved.Count - 1 do
                Moved.Items[i].Net := NewNet;
            PCBServer.PostProcess;
            Total := Total + Moved.Count;
            OldNet := NetByName(Board, OldName);
            if (OldNet <> nil) then Gone.Add(OldNet);
            PlaceLog(OldName + ' -> ' + NewName + ': ' + IntToStr(Moved.Count));
        end;
    end;
    PCBServer.PreProcess;
    for i := 0 to Gone.Count - 1 do
        Board.RemovePCBObject(Gone.Items[i]);
    PCBServer.PostProcess;
    Board.ViewManager_FullUpdate;
    Doc.Modified := True;
    PlaceFinish('{"success": true, "objects": ' + IntToStr(Total) + ', "nets_removed": ' + IntToStr(Gone.Count) +
                ', "missing_targets": ' + IntToStr(Missing) + '}');
end;

// ------------------------------------------------------------- SetNets
// ape_setnets.txt: the board's path, then TRK|layer|x1|y1|x2|y2|net, VIA|x|y|net and ARC|layer|xc|yc|r|net (free copper, matched exactly,
// coordinates from the board origin). Gives each listed object that net. Nothing moves and nothing is saved.
procedure SetNets;
var
    Spec, Keys : TStringList;
    Path, Key : String;
    Board : IPCB_Board;
    Doc : IServerDocument;
    It : IPCB_BoardIterator;
    Obj, Net : IDispatch;
    i, k, X0, Y0, Done, Missing : Integer;
begin
    LogLines := TStringList.Create;
    PlaceLog('SetNets start');
    Spec := TStringList.Create;
    Spec.LoadFromFile(BRIDGE + 'ape_setnets.txt');
    Path := Trim(Spec[0]);
    Doc := OpenDoc(Path);
    Client.ShowDocument(Doc);
    Board := PCBServer.GetPCBBoardByPath(Path);
    X0 := Board.XOrigin;
    Y0 := Board.YOrigin;
    Keys := TStringList.Create;
    for i := 1 to Spec.Count - 1 do
        if (Trim(Spec[i]) <> '') then Keys.Add(Trim(Spec[i]));
    Done := 0;
    Missing := 0;
    PCBServer.PreProcess;
    It := Board.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eViaObject, eTrackObject, eArcObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    Obj := It.FirstPCBObject;
    while (Obj <> nil) do
    begin
        if (not Obj.InComponent) and (not Obj.InPolygon) then
        begin
            if (Obj.ObjectId = eViaObject) then
                Key := 'VIA|' + IntToStr(Obj.x - X0) + '|' + IntToStr(Obj.y - Y0)
            else if (Obj.ObjectId = eArcObject) then
                Key := 'ARC|' + IntToStr(Obj.Layer) + '|' + IntToStr(Obj.XCenter - X0) + '|' + IntToStr(Obj.YCenter - Y0) +
                       '|' + IntToStr(Obj.Radius)
            else
                Key := 'TRK|' + IntToStr(Obj.Layer) + '|' + IntToStr(Obj.x1 - X0) + '|' + IntToStr(Obj.y1 - Y0) +
                       '|' + IntToStr(Obj.x2 - X0) + '|' + IntToStr(Obj.y2 - Y0);
            for k := 0 to Keys.Count - 1 do
                if (Copy(Keys[k], 1, Length(Key) + 1) = Key + '|') then
                begin
                    Net := NetByName(Board, Copy(Keys[k], Length(Key) + 2, Length(Keys[k])));
                    if (Net <> nil) then
                    begin
                        // Obj.Net := Net alone shows in Altium but is saved as No Net: the net has to hold the object
                        PCBServer.SendMessageToRobots(Obj.I_ObjectAddress, c_Broadcast, PCBM_BeginModify, c_NoEventData);
                        Net.AddPCBObject(Obj);
                        PCBServer.SendMessageToRobots(Obj.I_ObjectAddress, c_Broadcast, PCBM_EndModify, c_NoEventData);
                        Done := Done + 1;
                    end
                    else
                        Missing := Missing + 1;
                end;
        end;
        Obj := It.NextPCBObject;
    end;
    Board.BoardIterator_Destroy(It);
    PCBServer.PostProcess;
    Board.ViewManager_FullUpdate;
    Doc.Modified := True;
    PlaceLog('set ' + IntToStr(Done) + ' of ' + IntToStr(Keys.Count));
    PlaceFinish('{"success": true, "listed": ' + IntToStr(Keys.Count) + ', "set": ' + IntToStr(Done) +
                ', "missing_nets": ' + IntToStr(Missing) + '}');
end;

// ------------------------------------------------------------- AddTracks
// ape_addtracks.txt: the board's path, then ADD|TRK|layer|x1|y1|x2|y2|width|net (coordinates from the board origin).
// Adds the tracks and nothing else: no polygon is repoured and nothing is saved.
procedure AddTracks;
var
    Spec : TStringList;
    Path, Rec : String;
    Board : IPCB_Board;
    Doc : IServerDocument;
    Net : IDispatch;
    Trk : IPCB_Track;
    i, X0, Y0, Tracks, Missing : Integer;
begin
    LogLines := TStringList.Create;
    PlaceLog('AddTracks start');
    Spec := TStringList.Create;
    Spec.LoadFromFile(BRIDGE + 'ape_addtracks.txt');
    Path := Trim(Spec[0]);
    Doc := OpenDoc(Path);
    Client.ShowDocument(Doc);
    Board := PCBServer.GetPCBBoardByPath(Path);
    X0 := Board.XOrigin;
    Y0 := Board.YOrigin;
    Tracks := 0;
    Missing := 0;
    PCBServer.PreProcess;
    for i := 1 to Spec.Count - 1 do
    begin
        Rec := Trim(Spec[i]);
        if (Field(Rec, 0) = 'ADD') and (Field(Rec, 1) = 'TRK') then
        begin
            Net := NetByName(Board, Field(Rec, 8));
            if (Net = nil) then
                Missing := Missing + 1
            else
            begin
                Trk := PCBServer.PCBObjectFactory(eTrackObject, eNoDimension, eCreate_Default);
                Trk.Layer := StrToInt(Field(Rec, 2));
                Trk.x1 := X0 + StrToInt(Field(Rec, 3));
                Trk.y1 := Y0 + StrToInt(Field(Rec, 4));
                Trk.x2 := X0 + StrToInt(Field(Rec, 5));
                Trk.y2 := Y0 + StrToInt(Field(Rec, 6));
                Trk.Width := StrToInt(Field(Rec, 7));
                Trk.Net := Net;
                Board.AddPCBObject(Trk);
                Tracks := Tracks + 1;
            end;
        end;
    end;
    PCBServer.PostProcess;
    Board.ViewManager_FullUpdate;
    Doc.Modified := True;
    PlaceFinish('{"success": true, "tracks": ' + IntToStr(Tracks) + ', "missing_nets": ' + IntToStr(Missing) + '}');
end;

// ------------------------------------------------------------- DeletePolys
// ape_delpolys.txt: the board's path, then POLY|layer|pour index|net per polygon to delete. Nothing else changes and
// nothing is saved (ApplyChange after it repours and saves).
procedure DeletePolys;
var
    Spec, Keys : TStringList;
    Path, Key : String;
    Board : IPCB_Board;
    Doc : IServerDocument;
    It : IPCB_BoardIterator;
    Obj : IDispatch;
    DelList : TInterfaceList;
    i : Integer;
begin
    LogLines := TStringList.Create;
    PlaceLog('DeletePolys start');
    Spec := TStringList.Create;
    Spec.LoadFromFile(BRIDGE + 'ape_delpolys.txt');
    Path := Trim(Spec[0]);
    Doc := OpenDoc(Path);
    Client.ShowDocument(Doc);
    Board := PCBServer.GetPCBBoardByPath(Path);
    Keys := TStringList.Create;
    for i := 1 to Spec.Count - 1 do
        if (Trim(Spec[i]) <> '') then Keys.Add(Trim(Spec[i]));
    DelList := TInterfaceList.Create;
    It := Board.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(ePolyObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    Obj := It.FirstPCBObject;
    while (Obj <> nil) do
    begin
        if (Obj.Net <> nil) then
        begin
            Key := 'POLY|' + IntToStr(Obj.Layer) + '|' + IntToStr(Obj.PourIndex) + '|' + Obj.Net.Name;
            if (Keys.IndexOf(Key) >= 0) then DelList.Add(Obj);
        end;
        Obj := It.NextPCBObject;
    end;
    Board.BoardIterator_Destroy(It);
    PCBServer.PreProcess;
    for i := 0 to DelList.Count - 1 do
        Board.RemovePCBObject(DelList.Items[i]);
    PCBServer.PostProcess;
    Board.ViewManager_FullUpdate;
    Doc.Modified := True;
    PlaceFinish('{"success": true, "listed": ' + IntToStr(Keys.Count) + ', "deleted": ' + IntToStr(DelList.Count) + '}');
end;

// ------------------------------------------------------------- ApplyChange
// ape_change.txt: the board's path, then DEL|TRK|layer|x1|y1|x2|y2 and DEL|VIA|x|y (free copper, matched exactly), then
// ADD|VIA|x|y|hole|dia|net and ADD|TRK|layer|x1|y1|x2|y2|width|net. Coordinates from the board origin. Rebuilds every
// polygon after, and saves once at the end, so a failure part way leaves the saved file as it was.
procedure ApplyChange;
var
    Spec, Keys : TStringList;
    Path, Key, Rec, Name, CurName : String;
    Board : IPCB_Board;
    Doc : IServerDocument;
    It : IPCB_BoardIterator;
    Obj, Net : IDispatch;
    DelList, PolyList : TInterfaceList;
    Via : IPCB_Via;
    Trk : IPCB_Track;
    i, X0, Y0, Listed, Removed, Vias, Tracks, Polys : Integer;
begin
    LogLines := TStringList.Create;
    PlaceLog('ApplyChange start');
    Spec := TStringList.Create;
    Spec.LoadFromFile(BRIDGE + 'ape_change.txt');
    Path := Trim(Spec[0]);
    Doc := OpenDoc(Path);
    Client.ShowDocument(Doc);
    Board := PCBServer.GetPCBBoardByPath(Path);
    X0 := Board.XOrigin;
    Y0 := Board.YOrigin;
    Keys := TStringList.Create;
    Keys.Sorted := True;
    for i := 1 to Spec.Count - 1 do
        if (Field(Spec[i], 0) = 'DEL') then Keys.Add(Copy(Trim(Spec[i]), 5, Length(Spec[i])));
    Listed := Keys.Count;
    DelList := TInterfaceList.Create;
    It := Board.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eViaObject, eTrackObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    Obj := It.FirstPCBObject;
    while (Obj <> nil) do
    begin
        if (not Obj.InComponent) and (not Obj.InPolygon) then
        begin
            if (Obj.ObjectId = eViaObject) then
                Key := 'VIA|' + IntToStr(Obj.x - X0) + '|' + IntToStr(Obj.y - Y0)
            else
                Key := 'TRK|' + IntToStr(Obj.Layer) + '|' + IntToStr(Obj.x1 - X0) + '|' + IntToStr(Obj.y1 - Y0) +
                       '|' + IntToStr(Obj.x2 - X0) + '|' + IntToStr(Obj.y2 - Y0);
            if (Keys.IndexOf(Key) >= 0) then DelList.Add(Obj);
        end;
        Obj := It.NextPCBObject;
    end;
    Board.BoardIterator_Destroy(It);
    Removed := DelList.Count;
    PlaceLog('removing ' + IntToStr(Removed) + ' of ' + IntToStr(Listed));
    PCBServer.PreProcess;
    for i := 0 to DelList.Count - 1 do
        Board.RemovePCBObject(DelList.Items[i]);
    PCBServer.PostProcess;
    PlaceLog('adding');
    Vias := 0;
    Tracks := 0;
    CurName := '';
    Net := nil;
    PCBServer.PreProcess;
    for i := 1 to Spec.Count - 1 do
    begin
        Rec := Spec[i];
        if (Field(Rec, 0) = 'ADD') and (Field(Rec, 1) = 'VIA') then
        begin
            Name := Field(Rec, 6);
            if (Name <> CurName) then
            begin
                Net := NetByName(Board, Name);
                CurName := Name;
            end;
            Via := PCBServer.PCBObjectFactory(eViaObject, eNoDimension, eCreate_Default);
            Via.x := X0 + StrToInt(Field(Rec, 2));
            Via.y := Y0 + StrToInt(Field(Rec, 3));
            Via.HoleSize := StrToInt(Field(Rec, 4));
            Via.Size := StrToInt(Field(Rec, 5));
            Via.LowLayer := eBottomLayer;
            Via.HighLayer := eTopLayer;
            Via.Net := Net;
            Via.IsTenting_Top := True;
            Via.IsTenting_Bottom := True;
            Board.AddPCBObject(Via);
            Vias := Vias + 1;
        end
        else if (Field(Rec, 0) = 'ADD') and (Field(Rec, 1) = 'TRK') then
        begin
            Name := Field(Rec, 8);
            if (Name <> CurName) then
            begin
                Net := NetByName(Board, Name);
                CurName := Name;
            end;
            Trk := PCBServer.PCBObjectFactory(eTrackObject, eNoDimension, eCreate_Default);
            Trk.Layer := StrToInt(Field(Rec, 2));
            Trk.x1 := X0 + StrToInt(Field(Rec, 3));
            Trk.y1 := Y0 + StrToInt(Field(Rec, 4));
            Trk.x2 := X0 + StrToInt(Field(Rec, 5));
            Trk.y2 := Y0 + StrToInt(Field(Rec, 6));
            Trk.Width := StrToInt(Field(Rec, 7));
            Trk.Net := Net;
            Board.AddPCBObject(Trk);
            Tracks := Tracks + 1;
        end;
    end;
    PCBServer.PostProcess;
    PlaceLog('vias ' + IntToStr(Vias) + ', tracks ' + IntToStr(Tracks));
    PolyList := TInterfaceList.Create;
    It := Board.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(ePolyObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    Obj := It.FirstPCBObject;
    while (Obj <> nil) do
    begin
        PolyList.Add(Obj);
        Obj := It.NextPCBObject;
    end;
    Board.BoardIterator_Destroy(It);
    Polys := 0;
    for i := 0 to PolyList.Count - 1 do
    begin
        PolyList.Items[i].Rebuild;
        Polys := Polys + 1;
        if (Polys mod 5 = 0) then PlaceLog('polygons ' + IntToStr(Polys));
    end;
    PlaceLog('polygons ' + IntToStr(Polys));
    Board.ViewManager_FullUpdate;
    Doc.Modified := True;
    Doc.DoFileSave('');
    PlaceFinish('{"success": true, "listed": ' + IntToStr(Listed) + ', "removed": ' + IntToStr(Removed) + ', "vias": ' +
                IntToStr(Vias) + ', "tracks": ' + IntToStr(Tracks) + ', "polygons": ' + IntToStr(Polys) + '}');
end;

// ------------------------------------------------------------- DumpKeys
// Read-only: logs the keys ApplyChange would build for free tracks and vias in one window, and the document's path.
procedure DumpKeys;
var
    Spec : TStringList;
    Path, Key : String;
    Board : IPCB_Board;
    It : IPCB_BoardIterator;
    Obj : IDispatch;
    X0, Y0, n : Integer;
begin
    LogLines := TStringList.Create;
    PlaceLog('DumpKeys start');
    Spec := TStringList.Create;
    Spec.LoadFromFile(BRIDGE + 'ape_change.txt');
    Path := Trim(Spec[0]);
    Board := PCBServer.GetPCBBoardByPath(Path);
    if (Board = nil) then
    begin
        PlaceLog('no board at ' + Path);
        PlaceFinish('{"success": false}');
        Exit;
    end;
    X0 := Board.XOrigin;
    Y0 := Board.YOrigin;
    PlaceLog('board ' + Board.FileName + ' origin ' + IntToStr(X0) + ' ' + IntToStr(Y0));
    n := 0;
    It := Board.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eViaObject, eTrackObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    Obj := It.FirstPCBObject;
    while (Obj <> nil) do
    begin
        if (not Obj.InComponent) and (not Obj.InPolygon) and (n < 40) then
        begin
            if (Obj.ObjectId = eViaObject) then
            begin
                if (Abs(Obj.x - X0 - 18740157) < 300000) and (Abs(Obj.y - Y0 - 13700787) < 300000) then
                begin
                    PlaceLog('VIA|' + IntToStr(Obj.x - X0) + '|' + IntToStr(Obj.y - Y0));
                    n := n + 1;
                end;
            end
            else if (Abs(Obj.x1 - X0 - 18740157) < 300000) and (Abs(Obj.y1 - Y0 - 13700787) < 300000) then
            begin
                PlaceLog('TRK|' + IntToStr(Obj.Layer) + '|' + IntToStr(Obj.x1 - X0) + '|' + IntToStr(Obj.y1 - Y0) +
                         '|' + IntToStr(Obj.x2 - X0) + '|' + IntToStr(Obj.y2 - Y0));
                n := n + 1;
            end;
        end;
        Obj := It.NextPCBObject;
    end;
    Board.BoardIterator_Destroy(It);
    PlaceFinish('{"success": true, "logged": ' + IntToStr(n) + '}');
end;

// ------------------------------------------------------------- CheckChange
// Read-only: how many of ape_change.txt's DEL objects are still on the open board, and how many copies of each ADD object.
procedure CheckChange;
var
    Spec, Dels, Adds, Seen : TStringList;
    Path, Key, Rec : String;
    Board : IPCB_Board;
    Doc : IServerDocument;
    It : IPCB_BoardIterator;
    Obj : IDispatch;
    i, X0, Y0, DelLeft, AddFound, AddDup : Integer;
begin
    LogLines := TStringList.Create;
    PlaceLog('CheckChange start');
    Spec := TStringList.Create;
    Spec.LoadFromFile(BRIDGE + 'ape_change.txt');
    Path := Trim(Spec[0]);
    Board := PCBServer.GetPCBBoardByPath(Path);
    X0 := Board.XOrigin;
    Y0 := Board.YOrigin;
    Dels := TStringList.Create;
    Dels.Sorted := True;
    Adds := TStringList.Create;
    Adds.Sorted := True;
    Seen := TStringList.Create;
    for i := 1 to Spec.Count - 1 do
    begin
        Rec := Spec[i];
        if (Field(Rec, 0) = 'DEL') then Dels.Add(Copy(Trim(Rec), 5, Length(Rec)))
        else if (Field(Rec, 0) = 'ADD') and (Field(Rec, 1) = 'VIA') then Adds.Add('VIA|' + Field(Rec, 2) + '|' + Field(Rec, 3))
        else if (Field(Rec, 0) = 'ADD') then
            Adds.Add('TRK|' + Field(Rec, 2) + '|' + Field(Rec, 3) + '|' + Field(Rec, 4) + '|' + Field(Rec, 5) + '|' + Field(Rec, 6));
    end;
    DelLeft := 0;
    AddFound := 0;
    It := Board.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eViaObject, eTrackObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    Obj := It.FirstPCBObject;
    while (Obj <> nil) do
    begin
        if (not Obj.InComponent) and (not Obj.InPolygon) then
        begin
            if (Obj.ObjectId = eViaObject) then
                Key := 'VIA|' + IntToStr(Obj.x - X0) + '|' + IntToStr(Obj.y - Y0)
            else
                Key := 'TRK|' + IntToStr(Obj.Layer) + '|' + IntToStr(Obj.x1 - X0) + '|' + IntToStr(Obj.y1 - Y0) +
                       '|' + IntToStr(Obj.x2 - X0) + '|' + IntToStr(Obj.y2 - Y0);
            if (Dels.IndexOf(Key) >= 0) then DelLeft := DelLeft + 1;
            if (Adds.IndexOf(Key) >= 0) then
            begin
                AddFound := AddFound + 1;
                Seen.Add(Key);
            end;
        end;
        Obj := It.NextPCBObject;
    end;
    Board.BoardIterator_Destroy(It);
    Seen.Sorted := True;
    AddDup := 0;
    for i := 1 to Seen.Count - 1 do
        if (Seen[i] = Seen[i - 1]) then AddDup := AddDup + 1;
    Doc := Client.GetDocumentByPath(Path);
    if (Doc <> nil) then
    begin
        if Doc.Modified then PlaceLog('document is modified, not saved') else PlaceLog('document matches its last save');
    end;
    PlaceFinish('{"success": true, "dels_listed": ' + IntToStr(Dels.Count) + ', "dels_left": ' + IntToStr(DelLeft) +
                ', "adds_listed": ' + IntToStr(Adds.Count) + ', "adds_found": ' + IntToStr(AddFound) + ', "duplicate_copies": ' + IntToStr(AddDup) + '}');
end;

// ------------------------------------------------------------- RevertDoc
// Throws away the open board's unsaved changes: closes it without saving and opens the saved file again.
procedure RevertDoc;
var
    Spec : TStringList;
    Path : String;
    Doc : IServerDocument;
begin
    LogLines := TStringList.Create;
    PlaceLog('RevertDoc start');
    Spec := TStringList.Create;
    Spec.LoadFromFile(BRIDGE + 'ape_change.txt');
    Path := Trim(Spec[0]);
    Doc := Client.GetDocumentByPath(Path);
    if (Doc <> nil) then
    begin
        Doc.Modified := False;
        Client.CloseDocument(Doc);
        PlaceLog('closed without saving');
    end;
    Doc := Client.OpenDocument('PCB', Path);
    Client.ShowDocument(Doc);
    PlaceLog('opened ' + Path);
    PlaceFinish('{"success": true}');
end;

procedure PlacePower;
var
    Spec, Owned, Signets : TStringList;
    Rec, Kind, Name, Pts, Pair, CurName, Path : String;
    AX1, AY1, AX2, AY2, OX, OY : Integer;
    Board : IPCB_Board;
    Doc : IServerDocument;
    It : IPCB_BoardIterator;
    Obj, Net, Removed : IDispatch;
    DelList : TInterfaceList;
    Via : IPCB_Via;
    Trk : IPCB_Track;
    Poly : IPCB_Polygon;
    Seg : TPolySegment;
    PX, PY : TStringList;
    i, k, X0, Y0, Vias, Tracks, Polys, P1, P2 : Integer;
begin
    LogLines := TStringList.Create;
    PlaceLog('PlacePower start');
    Spec := TStringList.Create;
    Spec.LoadFromFile(BRIDGE + 'ape_place_power.txt');
    Path := Trim(Spec[0]);
    Doc := OpenDoc(Path);
    Client.ShowDocument(Doc);
    Board := PCBServer.GetPCBBoardByPath(Path);
    X0 := Board.XOrigin;
    Y0 := Board.YOrigin;
    Owned := TStringList.Create;
    Owned.Sorted := True;
    Signets := TStringList.Create;
    Signets.Sorted := True;
    AX1 := 0; AY1 := 0; AX2 := 0; AY2 := 0;
    for i := 1 to Spec.Count - 1 do
    begin
        if (Field(Spec[i], 0) = 'NET') then Owned.Add(Field(Spec[i], 1));
        if (Field(Spec[i], 0) = 'SIGNET') then Signets.Add(Field(Spec[i], 1));
        if (Field(Spec[i], 0) = 'AREA') then
        begin
            AX1 := X0 + StrToInt(Field(Spec[i], 1));
            AY1 := Y0 + StrToInt(Field(Spec[i], 2));
            AX2 := X0 + StrToInt(Field(Spec[i], 3));
            AY2 := Y0 + StrToInt(Field(Spec[i], 4));
        end;
    end;
    // ---- what an earlier run left
    DelList := TInterfaceList.Create;
    It := Board.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eViaObject, eTrackObject, ePolyObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    Obj := It.FirstPCBObject;
    while (Obj <> nil) do
    begin
        if (not Obj.InComponent) and (not Obj.InPolygon) then
            if (Obj.Net <> nil) then
            begin
                if (Owned.IndexOf(Obj.Net.Name) >= 0) then DelList.Add(Obj)
                else if (Signets.IndexOf(Obj.Net.Name) >= 0) then
                begin
                    if (Obj.ObjectId = eViaObject) then
                    begin
                        OX := Obj.x;
                        OY := Obj.y;
                    end
                    else if (Obj.ObjectId = eTrackObject) then
                    begin
                        OX := Obj.x1;
                        OY := Obj.y1;
                    end
                    else
                    begin
                        OX := AX1 - 1;
                        OY := AY1 - 1;
                    end;
                    if (OX >= AX1) and (OX <= AX2) and (OY >= AY1) and (OY <= AY2) then DelList.Add(Obj);
                end;
            end
            else if (Obj.ObjectId = ePolyObject) then
                // replacing a polygon can leave a shelved copy with no net behind it
                DelList.Add(Obj);
        Obj := It.NextPCBObject;
    end;
    Board.BoardIterator_Destroy(It);
    PlaceLog('removing ' + IntToStr(DelList.Count));
    PCBServer.PreProcess;
    for i := 0 to DelList.Count - 1 do
        Board.RemovePCBObject(DelList.Items[i]);
    PCBServer.PostProcess;
    PlaceLog('adding');
    Vias := 0;
    Tracks := 0;
    Polys := 0;
    CurName := '';
    Net := nil;
    PCBServer.PreProcess;
    for i := 1 to Spec.Count - 1 do
    begin
        Rec := Spec[i];
        Kind := Field(Rec, 0);
        if (Kind = 'VIA') then
        begin
            Name := Field(Rec, 5);
            if (Name <> CurName) then
            begin
                Net := NetByName(Board, Name);
                CurName := Name;
            end;
            Via := PCBServer.PCBObjectFactory(eViaObject, eNoDimension, eCreate_Default);
            Via.x := X0 + StrToInt(Field(Rec, 1));
            Via.y := Y0 + StrToInt(Field(Rec, 2));
            Via.HoleSize := StrToInt(Field(Rec, 3));
            Via.Size := StrToInt(Field(Rec, 4));
            Via.LowLayer := eBottomLayer;
            Via.HighLayer := eTopLayer;
            Via.Net := Net;
            Via.IsTenting_Top := True;
            Via.IsTenting_Bottom := True;
            Board.AddPCBObject(Via);
            Vias := Vias + 1;
        end
        else if (Kind = 'TRK') then
        begin
            Name := Field(Rec, 7);
            if (Name <> CurName) then
            begin
                Net := NetByName(Board, Name);
                CurName := Name;
            end;
            Trk := PCBServer.PCBObjectFactory(eTrackObject, eNoDimension, eCreate_Default);
            Trk.Layer := StrToInt(Field(Rec, 1));
            Trk.x1 := X0 + StrToInt(Field(Rec, 2));
            Trk.y1 := Y0 + StrToInt(Field(Rec, 3));
            Trk.x2 := X0 + StrToInt(Field(Rec, 4));
            Trk.y2 := Y0 + StrToInt(Field(Rec, 5));
            Trk.Width := StrToInt(Field(Rec, 6));
            Trk.Net := Net;
            Board.AddPCBObject(Trk);
            Tracks := Tracks + 1;
        end;
    end;
    PCBServer.PostProcess;
    PlaceLog('vias ' + IntToStr(Vias) + ', tracks ' + IntToStr(Tracks));
    // ---- polygons, in file order
    for i := 1 to Spec.Count - 1 do
    begin
        Rec := Spec[i];
        if (Field(Rec, 0) = 'POLY') then
        begin
            Name := Field(Rec, 2);
            Net := NetByName(Board, Name);
            Pts := Field(Rec, 4);
            PX := TStringList.Create;
            PY := TStringList.Create;
            while (Pts <> '') do
            begin
                P1 := Pos(';', Pts);
                if (P1 = 0) then
                begin
                    Pair := Pts;
                    Pts := '';
                end
                else
                begin
                    Pair := Copy(Pts, 1, P1 - 1);
                    Pts := Copy(Pts, P1 + 1, Length(Pts));
                end;
                P2 := Pos(',', Pair);
                PX.Add(Copy(Pair, 1, P2 - 1));
                PY.Add(Copy(Pair, P2 + 1, Length(Pair)));
            end;
            Poly := PCBServer.PCBObjectFactory(ePolyObject, eNoDimension, eCreate_Default);
            Poly.Layer := StrToInt(Field(Rec, 1));
            Poly.PolyHatchStyle := ePolySolid;
            Poly.Net := Net;
            Poly.RemoveDead := True;
            // Altium's defaults remove any piece under 2500 sq mil, connected or not, which is a 0.25 x 6 mm strip, and any
            // neck under 5 mil. Dead copper still goes; a neck stays down to JLC's 3.5 mil.
            Poly.RemoveIslandsByArea := False;
            Poly.RemoveNarrowNecks := True;
            Poly.NeckWidthThreshold := 35000;
            Poly.PourIndex := StrToInt(Field(Rec, 3));
            Poly.PointCount := PX.Count;
            for k := 0 to PX.Count do
            begin
                Seg := TPolySegment;
                Seg.Kind := ePolySegmentLine;
                Seg.vx := X0 + StrToInt(PX[k mod PX.Count]);
                Seg.vy := Y0 + StrToInt(PY[k mod PX.Count]);
                Poly.Segments[k] := Seg;
            end;
            Board.AddPCBObject(Poly);
            Poly.Rebuild;
            Polys := Polys + 1;
            PX.Free;
            PY.Free;
            if (Polys mod 10 = 0) then PlaceLog('polygons ' + IntToStr(Polys));
        end;
    end;
    Spec.Free;
    Owned.Free;
    Signets.Free;
    PlaceLog('polygons ' + IntToStr(Polys));
    Board.ViewManager_FullUpdate;
    Doc.Modified := True;
    Doc.DoFileSave('');
    PlaceFinish('{"success": true, "vias": ' + IntToStr(Vias) + ', "tracks": ' + IntToStr(Tracks) +
                ', "polygons": ' + IntToStr(Polys) + '}');
end;

// Put this into your Assets folder
// The best place is to put it in a Scripts/ Editor Scripts folder

using UnityEngine;
using System.Collections;
using System.Collections.Generic;
using System.IO;

public class NotifyForLockedFiles : UnityEditor.AssetModificationProcessor
{
    public static string[] OnWillSaveAssets(string[] paths)
    {
        List<string> pathsToSave = new List<string>();

        for (int i = 0; i < paths.Length; ++i)
        {
            FileInfo info = new FileInfo(paths[i]);
            if (info.IsReadOnly)
                UnityEditor.EditorUtility.DisplayDialog("File locked",
                paths[i] + " is locked by Anchorpoint to prevent conflicts.",
                "Ok");
            else
                pathsToSave.Add(paths[i]);
        }

        return pathsToSave.ToArray();
    }
}
